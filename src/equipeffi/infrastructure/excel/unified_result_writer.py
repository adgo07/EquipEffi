"""一次ZIP补丁写出泵与变压器结果，保留所有输入和非目标OOXML部件。"""
from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import uuid
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

from ...application.ports.batch_workbook import BatchRowOutcome
from .pump_result_writer import (
    ResultWorkbookExistsError,
    ResultWorkbookWriteError,
    _as_number,
    _patch_prefix,
    _row_edits,
    _sheet_target,
    _normalise_main_namespace,
    assert_main_namespace_semantics,
    assert_unique_references,
    cell_payloads as pump_cell_payloads,
    default_result_filename,
    patch_sheet_xml as patch_pump_sheet_xml,
    plan_namespace,
)
from .result_invariants import (
    InvariantViolation,
    assert_input_preserved,
    assert_non_main_elements_preserved,
    assert_result_payloads,
)
from .ooxml_reader import OOXMLWorkbook
from .template_resource import (
    PUMP_SHEET,
    PUMP_SHEET_CONTRACT,
    MOTOR_SHEET_CONTRACT,
    TEMPLATE_MANIFEST,
    TRANSFORMER_SHEET_CONTRACT,
    validate_v6_template,
)
from .worksheet_patch import (
    SheetStructureError,
    WorksheetPatch,
    column_number,
    cell_xml,
    outer_attributes,
)


TRANSFORMER_SHEET = str(TRANSFORMER_SHEET_CONTRACT["sheet_name"])
MOTOR_SHEET = str(MOTOR_SHEET_CONTRACT["sheet_name"])
_TRANSFORMER_RESULT_FIELDS = tuple(
    field for field in TRANSFORMER_SHEET_CONTRACT["fields"]
    if field.get("role") == "result")
_TRANSFORMER_THRESHOLD_FIELDS = tuple(
    (str(field["column"]), str(field["threshold_key"]))
    for field in _TRANSFORMER_RESULT_FIELDS if field.get("threshold_key"))
_TRANSFORMER_RESULT_BY_KEY = {
    str(field["result_key"]): str(field["column"])
    for field in _TRANSFORMER_RESULT_FIELDS if field.get("result_key")}
TRANSFORMER_RESULT_COLUMNS = tuple(
    str(field["column"]) for field in _TRANSFORMER_RESULT_FIELDS)
LEGAL_TRANSFORMER_CONCLUSIONS = frozenset({
    "1级", "2级", "3级", "未达3级", "不在范围", "无法判定",
})
_MOTOR_RESULT_FIELDS = tuple(
    field for field in MOTOR_SHEET_CONTRACT["fields"]
    if field.get("role") == "result")
_MOTOR_THRESHOLD_FIELDS = tuple(
    (str(field["column"]), str(field["threshold_key"]))
    for field in _MOTOR_RESULT_FIELDS if field.get("threshold_key"))
_MOTOR_RESULT_BY_KEY = {
    str(field["result_key"]): str(field["column"])
    for field in _MOTOR_RESULT_FIELDS if field.get("result_key")}
MOTOR_RESULT_COLUMNS = tuple(str(field["column"]) for field in _MOTOR_RESULT_FIELDS)
LEGAL_MOTOR_CONCLUSIONS = frozenset({
    "1级", "2级", "3级", "未达3级", "不在范围", "无法判定",
})
_BATCH_SUMMARY_LABELS = (
    "本次批量处理说明", "模板版本", "处理时间", "已评价Sheet",
    "未评价Sheet", "统计口径", "未评价提示", "软件区域标识",
)
_BATCH_OUTPUT_MARKER = "EQUIPEFFI_BATCH_OUTPUT_V1"
if (len(_TRANSFORMER_THRESHOLD_FIELDS) != 6
        or set(_TRANSFORMER_RESULT_BY_KEY) != {"conclusion", "messages"}):
    raise RuntimeError("变压器模板清单的结果字段契约不完整")
if (len(_MOTOR_THRESHOLD_FIELDS) != 3
        or set(_MOTOR_RESULT_BY_KEY) != {"conclusion", "messages"}):
    raise RuntimeError("电动机模板清单的结果字段契约不完整")
_TEMP_SUFFIX = ".equipeffi-tmp"
_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _result_columns(contract: dict) -> tuple[str, ...]:
    return tuple(str(field["column"]) for field in contract["fields"]
                 if field.get("role") == "result")


def _input_column_indexes(contract: dict) -> tuple[int, ...]:
    indexes: list[int] = []
    for field in contract["fields"]:
        if field.get("role") != "input":
            continue
        value = 0
        for char in str(field["column"]).upper():
            value = value * 26 + ord(char) - ord("A") + 1
        indexes.append(value - 1)
    return tuple(indexes)


def _blank_input_rows(source: Path, sheet_name: str, contract: dict,
                      *, excluded_rows: set[int]) -> set[int]:
    """Find rows the Reader skips using only declared input values.

    Worksheet style, output formulas, row metadata, and cells outside the input
    contract do not enable a data row. Output rows returned by the Reader are
    explicitly excluded so formula/input errors still retain their diagnostics.
    """

    header_row = int(contract["header_row"])
    input_indexes = _input_column_indexes(contract)
    with OOXMLWorkbook(source) as workbook:
        grid = workbook.rows(sheet_name)
    result: set[int] = set()
    for row_number, values in enumerate(grid[header_row:], start=header_row + 1):
        if row_number in excluded_rows:
            continue
        if not any(index < len(values) and values[index] not in (None, "")
                   for index in input_indexes):
            result.add(row_number)
    return result


def _cell_has_payload(cell) -> bool:
    return any(child.ns_uri == _MAIN_NS and child.local in {"f", "v", "is"}
               for child in cell.element.children)


def _clear_blank_result_cells(
        xml: str, row_numbers: set[int], result_columns: tuple[str, ...]
        ) -> tuple[str, tuple[str, ...]]:
    """Clear existing software outputs on blank rows without inserting cells."""

    try:
        patch = WorksheetPatch(xml)
    except SheetStructureError as error:
        raise ResultWorkbookWriteError(
            f"空白行结果清理结构校验失败：{error}；拒绝产出结果工作簿") from error
    duplicates = patch.duplicate_references()
    if duplicates:
        raise ResultWorkbookWriteError(
            "输入工作表存在重复单元格坐标："
            f"{sorted(duplicates)[:10]}；拒绝清理结果")

    plan = plan_namespace(xml)
    edits: list[tuple[int, int, str]] = []
    cleared: list[str] = []
    for row_number in sorted(row_numbers):
        row = patch.rows.get(row_number)
        if row is None:
            continue
        by_reference = {cell.reference: cell for cell in row.cells if cell.reference}
        for column in result_columns:
            reference = f"{column}{row_number}"
            cell = by_reference.get(reference)
            if cell is None or not _cell_has_payload(cell):
                continue
            prefix = _patch_prefix(plan, cell.element.prefix, cell.element.ns_uri)
            edits.append((
                cell.start,
                cell.end,
                cell_xml(reference, cell.style, ("s", ""), prefix,
                         extra=outer_attributes(cell.element)),
            ))
            cleared.append(reference)

    if not edits:
        return xml, ()
    edits.sort(key=lambda item: (item[0], item[1]))
    previous_end = -1
    for start, end, _fragment in edits:
        if start < previous_end:
            raise ResultWorkbookWriteError("空白行结果清理补丁重叠，拒绝写回")
        previous_end = max(previous_end, end)
    result = _normalise_main_namespace(patch.apply(edits))
    try:
        assert_non_main_elements_preserved(xml, result)
        assert_unique_references(result)
        assert_main_namespace_semantics(result)
    except InvariantViolation as error:
        raise ResultWorkbookWriteError(
            f"空白行结果清理独立校验失败：{error}") from error
    return result, tuple(cleared)


def _assert_result_cells_cleared(xml: str, references: tuple[str, ...]) -> None:
    if not references:
        return
    try:
        patch = WorksheetPatch(xml)
    except SheetStructureError as error:
        raise InvariantViolation(f"结果工作表结构无效：{error}") from error
    for reference in references:
        row_number = int("".join(char for char in reference if char.isdigit()))
        row = patch.rows.get(row_number)
        cell = (next((item for item in row.cells
                      if item.reference == reference), None) if row else None)
        if cell is not None and _cell_has_payload(cell):
            raise InvariantViolation(f"空白输入行的旧结果仍存在：{reference}")


def _transformer_cell_payloads(
        outcome: BatchRowOutcome) -> dict[str, tuple[str, str]]:
    conclusion = str(outcome.conclusion or "").strip()
    is_displayable_conclusion = (
        conclusion in LEGAL_TRANSFORMER_CONCLUSIONS
        and not outcome.is_input_error
        and not outcome.is_execution_error
        and outcome.evaluation_status != "INVALID_INPUT")
    payloads: dict[str, tuple[str, str]] = {}
    for column, key in _TRANSFORMER_THRESHOLD_FIELDS:
        value = ((outcome.thresholds or {}).get(key)
                 if is_displayable_conclusion else None)
        if value is None:
            # Explicitly clear stale values from a previously evaluated workbook.
            payloads[column] = ("s", "")
            continue
        text = _as_number(value)
        if text is None:
            payloads[column] = ("s", "")
            continue
        try:
            Decimal(text)
        except (InvalidOperation, ValueError) as error:
            raise ResultWorkbookWriteError(
                f"变压器阈值 {key} 不是有效数值：{value!r}") from error
        payloads[column] = ("n", text)
    messages = [str(message) for message in (outcome.messages or ()) if message]
    if is_displayable_conclusion:
        result_conclusion = conclusion
    else:
        result_conclusion = ""
        fallback = conclusion or (
            "执行失败" if outcome.is_execution_error else
            "输入错误" if outcome.is_input_error
            or outcome.evaluation_status == "INVALID_INPUT" else "")
        if fallback and not any(
                message == fallback or message.startswith(fallback + "：")
                for message in messages):
            messages.insert(0, fallback)
    payloads[_TRANSFORMER_RESULT_BY_KEY["conclusion"]] = (
        "s", result_conclusion)
    payloads[_TRANSFORMER_RESULT_BY_KEY["messages"]] = (
        "s", "；".join(messages))
    return payloads


def patch_transformer_sheet_xml(
        xml: str, outcomes: dict[int, BatchRowOutcome]) -> str:
    """只写变压器结果列；不从输入重算阈值或等级。"""
    try:
        patch = WorksheetPatch(xml)
    except SheetStructureError as error:
        raise ResultWorkbookWriteError(
            f"结果写回结构校验失败：{error}；拒绝产出结果工作簿") from error

    missing = sorted(number for number in outcomes if number not in patch.rows)
    if missing:
        raise ResultWorkbookWriteError(
            "结果写回失败：无法在「变压器」Sheet中定位数据行 "
            f"{missing[:10]}（共 {len(missing)} 行）")
    duplicates = patch.duplicate_references()
    if duplicates:
        raise ResultWorkbookWriteError(
            "变压器输入工作表存在重复单元格坐标："
            f"{sorted(duplicates)[:10]}；拒绝写回")

    plan = plan_namespace(xml)
    edits: list[tuple[int, int, str]] = []
    for row_number in sorted(outcomes):
        edits.extend(_row_edits(
            patch, int(row_number), _transformer_cell_payloads(outcomes[row_number]), plan))
    edits.sort(key=lambda item: (item[0], item[1]))
    previous_end = -1
    for start, end, _fragment in edits:
        if start < previous_end:
            raise ResultWorkbookWriteError("变压器结果补丁区域重叠，拒绝写回")
        previous_end = max(previous_end, end)

    result = _normalise_main_namespace(patch.apply(edits))
    try:
        assert_non_main_elements_preserved(xml, result)
        assert_unique_references(result)
        assert_main_namespace_semantics(result)
    except InvariantViolation as error:
        raise ResultWorkbookWriteError(
            f"变压器结果写回独立校验失败：{error}") from error
    return result


def _motor_threshold_payload(value, key: str) -> tuple[str, str]:
    """Use the Application threshold state and display projection verbatim."""
    if not isinstance(value, dict):
        return ("s", "")
    state = value.get("state")
    if state == "NO_INDICATOR":
        return ("s", "—")
    if state == "NOT_COMPUTED":
        return ("s", "")
    if state != "AVAILABLE":
        return ("s", "")
    display = value.get("display_text")
    if display in (None, ""):
        raise ResultWorkbookWriteError(
            f"电动机阈值 {key} 标记为AVAILABLE但缺少display_text")
    try:
        return ("n", format(Decimal(str(display).strip()), "f"))
    except (InvalidOperation, ValueError) as error:
        raise ResultWorkbookWriteError(
            f"电动机阈值 {key} 的display_text不是有效数值：{display!r}") from error


def _motor_cell_payloads(outcome: BatchRowOutcome) -> dict[str, tuple[str, str]]:
    conclusion = str(outcome.conclusion or "").strip()
    is_displayable = (
        conclusion in LEGAL_MOTOR_CONCLUSIONS
        and not outcome.is_input_error
        and not outcome.is_execution_error
        and outcome.evaluation_status != "INVALID_INPUT")
    payloads: dict[str, tuple[str, str]] = {}
    for column, key in _MOTOR_THRESHOLD_FIELDS:
        threshold = (outcome.thresholds or {}).get(key)
        payloads[column] = (
            _motor_threshold_payload(threshold, key)
            if is_displayable else ("s", ""))
    messages = [str(message) for message in (outcome.messages or ()) if message]
    if is_displayable:
        result_conclusion = conclusion
    else:
        result_conclusion = ""
        fallback = conclusion or (
            "执行失败" if outcome.is_execution_error else
            "输入错误" if outcome.is_input_error
            or outcome.evaluation_status == "INVALID_INPUT" else "")
        if fallback and not any(
                message == fallback or message.startswith(fallback + "：")
                for message in messages):
            messages.insert(0, fallback)
    payloads[_MOTOR_RESULT_BY_KEY["conclusion"]] = ("s", result_conclusion)
    payloads[_MOTOR_RESULT_BY_KEY["messages"]] = ("s", "；".join(messages))
    return payloads


def _add_missing_motor_result_cells(
        xml: str, outcomes: dict[int, BatchRowOutcome]) -> str:
    """Create absent result cells with the matching column's template style."""
    try:
        patch = WorksheetPatch(xml)
    except SheetStructureError as error:
        raise ResultWorkbookWriteError(
            f"电动机结果写回结构校验失败：{error}；拒绝产出结果工作簿") from error

    missing_rows = sorted(number for number in outcomes if number not in patch.rows)
    if missing_rows:
        raise ResultWorkbookWriteError(
            "结果写回失败：无法在「电动机」Sheet中定位数据行 "
            f"{missing_rows[:10]}（共 {len(missing_rows)} 行）")
    duplicates = patch.duplicate_references()
    if duplicates:
        raise ResultWorkbookWriteError(
            "电动机输入工作表存在重复单元格坐标："
            f"{sorted(duplicates)[:10]}；拒绝写回")

    missing_by_row: dict[int, tuple[str, ...]] = {}
    for row_number in sorted(outcomes):
        row = patch.rows[row_number]
        present = {cell.reference for cell in row.cells if cell.reference}
        missing_columns = tuple(
            column for column in MOTOR_RESULT_COLUMNS
            if f"{column}{row_number}" not in present)
        if missing_columns:
            missing_by_row[row_number] = missing_columns
    if not missing_by_row:
        return xml

    table_ref = str(MOTOR_SHEET_CONTRACT.get("table", {}).get("ref", ""))
    range_match = re.fullmatch(r"[A-Z]+([1-9][0-9]*):[A-Z]+([1-9][0-9]*)",
                               table_ref)
    first_template_row = int(MOTOR_SHEET_CONTRACT.get("header_row", 0)) + 1
    last_template_row = max(patch.rows, default=first_template_row)
    if range_match is not None:
        first_template_row = max(first_template_row, int(range_match.group(1)) + 1)
        last_template_row = int(range_match.group(2))

    source_styles: dict[str, list[tuple[int, str]]] = {}
    for row_number in sorted(patch.rows):
        if not first_template_row <= row_number <= last_template_row:
            continue
        row = patch.rows[row_number]
        for cell in row.cells:
            match = re.fullmatch(r"([A-Z]+)[1-9][0-9]*", cell.reference or "")
            if (match is not None and match.group(1) in MOTOR_RESULT_COLUMNS
                    and cell.style is not None):
                source_styles.setdefault(match.group(1), []).append(
                    (row_number, cell.style))

    plan = plan_namespace(xml)
    edits: list[tuple[int, int, str]] = []
    for row_number, columns in missing_by_row.items():
        row = patch.rows[row_number]
        row_prefix = _patch_prefix(plan, row.prefix, row.element.ns_uri)
        for column in columns:
            candidates = source_styles.get(column, ())
            if not candidates:
                raise ResultWorkbookWriteError(
                    f"模板中找不到电动机结果列{column}的同列样式来源")
            _source_row, style = min(
                candidates, key=lambda item: (abs(item[0] - row_number), item[0]))
            target = column_number(column)
            insertion = row.body_end
            for cell in row.cells:
                split = re.fullmatch(r"([A-Z]+)[1-9][0-9]*", cell.reference or "")
                if split is not None and column_number(split.group(1)) > target:
                    insertion = cell.start
                    break
            reference = f"{column}{row_number}"
            edits.append((insertion, insertion,
                          cell_xml(reference, style, ("s", ""), row_prefix)))

    result = _normalise_main_namespace(patch.apply(edits))
    try:
        assert_non_main_elements_preserved(xml, result)
        assert_unique_references(result)
        assert_main_namespace_semantics(result)
    except InvariantViolation as error:
        raise ResultWorkbookWriteError(
            f"电动机缺失结果单元格补齐校验失败：{error}") from error
    return result


def patch_motor_sheet_xml(xml: str,
                          outcomes: dict[int, BatchRowOutcome], *,
                          threshold_style_map: dict[str, dict[str, str]] | None = None) -> str:
    """Write only GB 18613 result columns; never calculate Excel thresholds."""
    xml = _add_missing_motor_result_cells(xml, outcomes)
    threshold_cells: set[tuple[int, str, str]] = set()
    for row_number, outcome in outcomes.items():
        conclusion = str(outcome.conclusion or "").strip()
        displayable = (conclusion in LEGAL_MOTOR_CONCLUSIONS
                       and not outcome.is_input_error
                       and not outcome.is_execution_error
                       and outcome.evaluation_status != "INVALID_INPUT")
        if not displayable:
            continue
        for column, key in _MOTOR_THRESHOLD_FIELDS:
            threshold = (outcome.thresholds or {}).get(key)
            if (isinstance(threshold, dict)
                    and threshold.get("state") == "AVAILABLE"
                    and threshold.get("method") in {"DIRECT", "LINEAR_INTERPOLATION"}):
                threshold_cells.add((int(row_number), column,
                                     str(threshold["method"])))
    if threshold_cells:
        if not threshold_style_map and any(
                method == "LINEAR_INTERPOLATION"
                for _row_number, _column, method in threshold_cells):
            raise ResultWorkbookWriteError(
                "电动机线性插值阈值缺少模板既有0.00格式样式映射")
        try:
            style_patch = WorksheetPatch(xml)
        except SheetStructureError as error:
            raise ResultWorkbookWriteError(
                f"电动机插值显示样式定位失败：{error}") from error
        style_edits: list[tuple[int, int, str]] = []
        for row_number, column, method in sorted(threshold_cells):
            row = style_patch.rows.get(row_number)
            cell = next((item for item in row.cells
                         if item.reference == f"{column}{row_number}"), None) if row else None
            if cell is None:
                raise ResultWorkbookWriteError(
                    f"无法为插值阈值定位模板格式单元格：{column}{row_number}")
            style = cell.style
            style_options = (threshold_style_map or {}).get(str(style or ""), {})
            target_style = style_options.get(method)
            if target_style is None:
                if method == "DIRECT":
                    # Direct lookups retain the template's variable-decimal
                    # format; do not impose the interpolation display scale.
                    continue
                raise ResultWorkbookWriteError(
                    f"模板单元格样式{style!r}没有可复用的0.00格式，拒绝丢失插值显示精度")
            attribute = cell.element.attribute("s")
            if attribute is None:
                raise ResultWorkbookWriteError(
                    f"插值阈值单元格缺少既有样式属性：{column}{row_number}")
            if attribute.value != target_style:
                style_edits.append((attribute.start, attribute.end,
                                    f"s={attribute.quote}{target_style}{attribute.quote}"))
        if style_edits:
            xml = style_patch.apply(style_edits)
    try:
        patch = WorksheetPatch(xml)
    except SheetStructureError as error:
        raise ResultWorkbookWriteError(
            f"电动机结果写回结构校验失败：{error}；拒绝产出结果工作簿") from error
    missing = sorted(number for number in outcomes if number not in patch.rows)
    if missing:
        raise ResultWorkbookWriteError(
            "结果写回失败：无法在「电动机」Sheet中定位数据行 "
            f"{missing[:10]}（共 {len(missing)} 行）")
    duplicates = patch.duplicate_references()
    if duplicates:
        raise ResultWorkbookWriteError(
            "电动机输入工作表存在重复单元格坐标："
            f"{sorted(duplicates)[:10]}；拒绝写回")
    plan = plan_namespace(xml)
    edits: list[tuple[int, int, str]] = []
    for row_number in sorted(outcomes):
        edits.extend(_row_edits(
            patch, int(row_number), _motor_cell_payloads(outcomes[row_number]), plan))
    edits.sort(key=lambda item: (item[0], item[1]))
    previous_end = -1
    for start, end, _fragment in edits:
        if start < previous_end:
            raise ResultWorkbookWriteError("电动机结果补丁区域重叠，拒绝写回")
        previous_end = max(previous_end, end)
    result = _normalise_main_namespace(patch.apply(edits))
    try:
        assert_non_main_elements_preserved(xml, result)
        assert_unique_references(result)
        assert_main_namespace_semantics(result)
    except InvariantViolation as error:
        raise ResultWorkbookWriteError(
            f"电动机结果写回独立校验失败：{error}") from error
    return result


def _motor_threshold_style_map(styles_xml: bytes,
                               motor_xml: bytes) -> dict[str, dict[str, str]]:
    """Map each motor result style to retained variable and existing 0.00 styles.

    The template builder retains the source workbook's original style records
    and appends variable-decimal numeric styles. Reusing the matching original
    style avoids adding to or changing the workbook-wide style table.
    """
    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    try:
        styles_root = ElementTree.fromstring(styles_xml)
        motor_root = ElementTree.fromstring(motor_xml)
    except ElementTree.ParseError as error:
        raise ResultWorkbookWriteError(f"电动机格式样式XML无效：{error}") from error
    cell_xfs = styles_root.find(f"{{{namespace}}}cellXfs")
    if cell_xfs is None:
        raise ResultWorkbookWriteError("电动机模板缺少cellXfs样式记录")
    formats = {
        str(node.attrib.get("numFmtId", "")): str(node.attrib.get("formatCode", ""))
        for node in styles_root.findall(
            f"{{{namespace}}}numFmts/{{{namespace}}}numFmt")
    }
    styles = list(cell_xfs.findall(f"{{{namespace}}}xf"))
    cells = motor_root.findall(
        f"{{{namespace}}}sheetData/{{{namespace}}}row/{{{namespace}}}c")
    current_style_ids = sorted({
        cell.attrib["s"] for cell in cells
        if cell.attrib.get("s", "").isdigit()
        and re.fullmatch(r"[NOP](?:[4-9]|[1-9][0-9]+)",
                         cell.attrib.get("r", ""))
    }, key=int)

    def visual_signature(style) -> tuple:
        attributes = tuple(sorted(
            (key, value) for key, value in style.attrib.items()
            if key not in {"numFmtId", "applyNumberFormat"}))
        children = tuple(
            (child.tag, tuple(sorted(child.attrib.items())), child.text or "",
             tuple((grandchild.tag, tuple(sorted(grandchild.attrib.items())),
                    grandchild.text or "") for grandchild in list(child)))
            for child in list(style)
            if child.tag in {f"{{{namespace}}}alignment", f"{{{namespace}}}protection"})
        return attributes, children

    mapping: dict[str, dict[str, str]] = {}
    if not current_style_ids:
        raise ResultWorkbookWriteError("电动机模板缺少N:P阈值格式样式来源")
    for current_style_id in current_style_ids:
        current_id = int(current_style_id)
        if current_id >= len(styles):
            raise ResultWorkbookWriteError(f"阈值样式索引越界：{current_id}")
        current = styles[current_id]
        current_visual = visual_signature(current)

        def candidates_for(predicate) -> list[str]:
            return [
                str(index) for index, candidate in enumerate(styles)
                if predicate(candidate)
                and visual_signature(candidate) == current_visual
            ]

        direct_candidates = candidates_for(
            lambda item: formats.get(item.attrib.get("numFmtId", ""))
            == "0.###############")
        interpolation_candidates = candidates_for(
            lambda item: (item.attrib.get("numFmtId") == "2"
                          or formats.get(item.attrib.get("numFmtId", "")) == "0.00"))
        if not direct_candidates or not interpolation_candidates:
            raise ResultWorkbookWriteError(
                f"阈值样式{current_id}没有匹配的可变精度/0.00既有样式")
        selected = {
            "DIRECT": direct_candidates[0],
            "LINEAR_INTERPOLATION": interpolation_candidates[0],
        }
        prior = mapping.get(str(current_id))
        if prior is not None and prior != selected:
            raise ResultWorkbookWriteError("阈值样式映射不一致")
        mapping[str(current_id)] = selected
    return mapping


def _batch_summary_values(batch_summary: dict | None,
                          template_version: str) -> dict[int, str]:
    if not isinstance(batch_summary, dict):
        raise ResultWorkbookWriteError("批次说明必须是Application提供的映射")

    def count(key: str) -> int:
        raw = batch_summary.get(key, 0)
        try:
            return int(raw or 0)
        except (TypeError, ValueError, OverflowError) as error:
            raise ResultWorkbookWriteError(f"批次说明字段{key}不是整数") from error

    sheets = batch_summary.get("sheets")
    sheets = sheets if isinstance(sheets, list) else []
    evaluated_sheets = [
        str(item.get("sheet_name", "")) for item in sheets
        if isinstance(item, dict) and count_from(item.get("data_row_count", 0)) > 0
        and item.get("sheet_name")]
    unprocessed = batch_summary.get("unprocessed_sheets")
    unprocessed = ([str(item) for item in unprocessed]
                   if isinstance(unprocessed, (list, tuple)) else [])
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    statistic = (
        f"行数 {count('data_row_count')}；总数量 {count('total_quantity')} 台；"
        f"已形成结论 {count('concluded_rows')} 行 / {count('evaluated_quantity')} 台；"
        f"未形成结论 {count('unevaluated_rows')} 行；"
        f"输入错误 {count('input_error_rows')} 行；执行失败 {count('execution_error_rows')} 行。"
    )
    warning = ("以下Sheet未评价，内容保留原样：" + "、".join(unprocessed)
               if unprocessed else "无未评价Sheet。")
    return {
        27: "EquipEffi批量评价输出区；原始输入工作簿未覆盖。",
        28: template_version or "未知",
        29: now,
        30: "、".join(evaluated_sheets) or "无",
        31: "、".join(unprocessed) or "无",
        32: statistic,
        33: warning,
        34: _BATCH_OUTPUT_MARKER,
    }


def count_from(raw: object) -> int:
    try:
        return int(raw or 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def _patch_batch_summary_xml(
        xml: str, values: dict[int, str], *,
        region_values: dict[int, tuple[object, object]]) -> str:
    """Patch only A27:B34, inserting the range for older blank templates."""
    try:
        patch = WorksheetPatch(xml)
    except SheetStructureError as error:
        raise ResultWorkbookWriteError(
            f"模板说明Sheet结构校验失败：{error}；拒绝产出结果工作簿") from error
    duplicates = patch.duplicate_references()
    if duplicates:
        raise ResultWorkbookWriteError(
            "模板说明Sheet存在重复单元格坐标："
            f"{sorted(duplicates)[:10]}；拒绝写入批次说明")

    row_numbers = tuple(range(27, 35))
    complete_rows = all(number in patch.rows for number in row_numbers)
    existing_rows = any(number in patch.rows for number in row_numbers)
    labels = tuple(str(region_values.get(number, ("", ""))[0] or "")
                   for number in row_numbers)
    content = tuple(region_values.get(number, ("", ""))[1]
                    for number in row_numbers)
    marker_exists = content[-1] == _BATCH_OUTPUT_MARKER
    labels_are_template = labels == _BATCH_SUMMARY_LABELS
    region_is_blank = all(value in (None, "") for value in (*labels, *content))

    if complete_rows:
        if marker_exists:
            if not labels_are_template:
                raise ResultWorkbookWriteError(
                    "批次说明区域标识存在但固定标签被修改，拒绝覆盖")
        elif not region_is_blank and not (
                labels_are_template and all(value in (None, "") for value in content)):
            raise ResultWorkbookWriteError(
                "模板说明A27:B34已有内容且无软件区域标识，拒绝覆盖用户内容")
        if not marker_exists:
            # Cached blanks are not enough: a formula in this range could
            # generate user content after recalculation.
            for number in row_numbers:
                row = patch.rows[number]
                for cell in row.cells:
                    if cell.reference in {f"A{number}", f"B{number}"} and any(
                            child.local == "f" and child.is_main_namespace
                            for child in cell.element.children):
                        raise ResultWorkbookWriteError(
                            "模板说明A27:B34含公式，拒绝覆盖用户内容")
        plan = plan_namespace(xml)
        edits: list[tuple[int, int, str]] = []
        for offset, number in enumerate(row_numbers):
            edits.extend(_row_edits(
                patch, number,
                {"A": ("s", _BATCH_SUMMARY_LABELS[offset]),
                 "B": ("s", values[number])}, plan))
        edits.sort(key=lambda item: item[0])
        result = _normalise_main_namespace(patch.apply(edits))
    else:
        # The older V6/V6.1 templates have no rows 27–34. If someone has
        # partially constructed that range, do not infer which cells they own.
        if existing_rows or not region_is_blank:
            raise ResultWorkbookWriteError(
                "模板说明A27:B34结构不完整且含有内容，拒绝覆盖用户内容")
        sheet_data = next((child for child in patch.root.children
                           if child.local == "sheetData" and child.is_main_namespace), None)
        if sheet_data is None or sheet_data.kind == "empty":
            raise ResultWorkbookWriteError("模板说明缺少可补丁的sheetData")
        existing_row = patch.rows.get(24)
        if existing_row is None:
            raise ResultWorkbookWriteError("旧模板缺少模板说明样式来源行")
        by_ref = {cell.reference: cell for cell in existing_row.cells if cell.reference}
        style_a = by_ref.get("A24").style if by_ref.get("A24") else None
        style_b = by_ref.get("B24").style if by_ref.get("B24") else None
        plan = plan_namespace(xml)
        prefix = _patch_prefix(plan, existing_row.prefix, existing_row.element.ns_uri)
        row_tag = f"{prefix}:row" if prefix else "row"
        heights = {27: "22", 28: "20", 29: "20", 30: "28", 31: "28", 32: "34", 33: "34", 34: "20"}
        fragments: list[str] = []
        for offset, number in enumerate(row_numbers):
            cell_a = cell_xml(f"A{number}", style_a,
                              ("s", _BATCH_SUMMARY_LABELS[offset]), prefix)
            cell_b = cell_xml(f"B{number}", style_b, ("s", values[number]), prefix)
            fragments.append(
                f'<{row_tag} r="{number}" spans="1:8" ht="{heights[number]}" '
                f'customHeight="1">{cell_a}{cell_b}</{row_tag}>')
        closing = f"</{sheet_data.qname}>"
        insert_at = sheet_data.end - len(closing)
        if insert_at < sheet_data.tag_end:
            raise ResultWorkbookWriteError("模板说明sheetData无法安全插入批次说明行")
        edits = [(insert_at, insert_at, "".join(fragments))]
        dimension = next((child for child in patch.root.children
                           if child.local == "dimension" and child.is_main_namespace), None)
        if dimension is not None:
            attribute = dimension.attribute("ref")
            if attribute is not None:
                edits.append((attribute.start, attribute.end, 'ref="A1:H34"'))
        result = _normalise_main_namespace(patch.apply(edits))

    try:
        assert_non_main_elements_preserved(xml, result)
        assert_unique_references(result)
        assert_main_namespace_semantics(result)
    except InvariantViolation as error:
        raise ResultWorkbookWriteError(f"批次说明写回独立校验失败：{error}") from error
    return result


class UnifiedResultWorkbookWriter:
    """在同一个ZIP重写周期内补丁所有已接通Sheet，并原子提交新工作簿。"""

    def default_destination(self, source: Path) -> Path:
        source = Path(source)
        return source.with_name(default_result_filename(source))

    def write(self, source: Path,
              outcomes_by_sheet: dict[str, dict[int, BatchRowOutcome]],
              destination: Path, *, overwrite: bool = False,
              batch_summary: dict | None = None) -> Path:
        source = Path(source)
        destination = Path(destination)
        if source.resolve() == destination.resolve():
            raise ValueError("结果工作簿不得覆盖原始输入文件")
        if destination.exists() and not overwrite:
            raise ResultWorkbookExistsError(
                f"结果工作簿已存在，不得静默覆盖：{destination}")

        validation = validate_v6_template(source, check_pump_sheet=False)
        if not validation.is_valid:
            raise ResultWorkbookWriteError(validation.message)
        identity = validation.identity or {}
        entry = next((item for item in TEMPLATE_MANIFEST["templates"]
                      if item.get("template_id") == identity.get("template_id")
                      and item.get("template_version") == identity.get("template_version")),
                     None)
        if entry is None:
            raise ResultWorkbookWriteError("工作簿模板身份未在Manifest登记")

        sheet_contracts = {
            str(sheet.get("sheet_name")): sheet
            for sheet in entry.get("sheets", ())
        }
        unknown = sorted(set(outcomes_by_sheet) - set(sheet_contracts))
        if unknown:
            raise ResultWorkbookWriteError(
                "结果包含未登记的工作表：" + "、".join(unknown))

        selected: dict[str, dict[int, BatchRowOutcome]] = {}
        version = str(identity.get("template_version", ""))
        for name, outcomes in outcomes_by_sheet.items():
            contract = sheet_contracts[name]
            if contract.get("status") != "CONNECTED":
                if outcomes:
                    raise ResultWorkbookWriteError(
                        f"工作表「{name}」尚未接通，不能写入结果")
                continue
            supported_sheet_ids = {"centrifugal_pump", "transformer"}
            if version == "V6.2":
                supported_sheet_ids.add("motor")
            if contract.get("sheet_id") not in supported_sheet_ids:
                if outcomes:
                    raise ResultWorkbookWriteError(
                        f"工作表「{name}」没有结果写入适配器")
                continue
            # Empty outcome maps are meaningful: the application passes each
            # connected sheet, including an entirely blank one, so stale output
            # values can be removed from the new workbook.
            selected[name] = outcomes

        with ZipFile(source) as archive:
            entries = [(info, archive.read(info.filename))
                       for info in archive.infolist()]
            names = [info.filename for info, _ in entries]
            if len(names) != len(set(names)):
                raise ResultWorkbookWriteError("输入工作簿包含重复ZIP部件名称")
            targets = {name: _sheet_target(archive, name) for name in selected}
            notes_sheet = next((str(sheet.get("sheet_name"))
                                for sheet in entry.get("sheets", ())
                                if sheet.get("sheet_id") == "template_notes"), None)
            if batch_summary is not None:
                if not notes_sheet:
                    raise ResultWorkbookWriteError("模板清单缺少批次说明Sheet")
                targets["__batch_summary__"] = _sheet_target(archive, notes_sheet)

        for name, target in targets.items():
            if not target or target not in names:
                raise ResultWorkbookWriteError(f"工作簿中找不到结果目标Sheet：{name}")

        by_part = {info.filename: data for info, data in entries}
        expected_by_part: dict[str, dict[str, str | None]] = {}
        expected_cleared_by_part: dict[str, tuple[str, ...]] = {}
        for name, outcomes in selected.items():
            part = targets[name]
            source_xml = by_part[part].decode("utf-8")
            contract = sheet_contracts[name]
            outcome_rows = {int(number) for number in outcomes}
            blank_rows = _blank_input_rows(
                source, name, contract, excluded_rows=outcome_rows)
            if name == PUMP_SHEET:
                result_xml = patch_pump_sheet_xml(source_xml, outcomes)
                result_columns = _result_columns(contract)
                expected: dict[str, str | None] = {}
                for row_number, outcome in outcomes.items():
                    for column, payload in pump_cell_payloads(outcome).items():
                        if payload is not None:
                            expected[f"{column}{row_number}"] = str(payload[1])
            elif name == TRANSFORMER_SHEET:
                result_xml = patch_transformer_sheet_xml(source_xml, outcomes)
                result_columns = TRANSFORMER_RESULT_COLUMNS
                expected = {
                    f"{column}{row_number}": str(payload[1])
                    for row_number, outcome in outcomes.items()
                    for column, payload in _transformer_cell_payloads(outcome).items()
                }
            elif name == MOTOR_SHEET and version == "V6.2":
                threshold_style_map = _motor_threshold_style_map(
                    by_part["xl/styles.xml"], by_part[part])
                result_xml = patch_motor_sheet_xml(
                    source_xml, outcomes,
                    threshold_style_map=threshold_style_map)
                result_columns = MOTOR_RESULT_COLUMNS
                expected = {
                    f"{column}{row_number}": str(payload[1])
                    for row_number, outcome in outcomes.items()
                    for column, payload in _motor_cell_payloads(outcome).items()
                }
            else:
                raise ResultWorkbookWriteError(f"没有工作表「{name}」的结果写入适配器")
            result_xml, cleared_references = _clear_blank_result_cells(
                result_xml, blank_rows, result_columns)
            try:
                assert_input_preserved(
                    source_xml, result_xml,
                    result_columns=result_columns,
                    row_numbers=outcome_rows | blank_rows)
                assert_result_payloads(result_xml, expected)
                _assert_result_cells_cleared(result_xml, cleared_references)
            except InvariantViolation as error:
                raise ResultWorkbookWriteError(
                    f"「{name}」结果写回独立校验失败：{error}") from error
            by_part[part] = result_xml.encode("utf-8")
            expected_by_part[part] = expected
            expected_cleared_by_part[part] = cleared_references

        if batch_summary is not None:
            notes_part = targets.get("__batch_summary__")
            if not notes_part or notes_part not in by_part:
                raise ResultWorkbookWriteError("工作簿中找不到固定批次说明区域")
            with OOXMLWorkbook(source) as workbook:
                notes_grid = workbook.rows(str(notes_sheet))
            region_values = {
                number: (
                    notes_grid[number - 1][0]
                    if number - 1 < len(notes_grid) and notes_grid[number - 1] else "",
                    notes_grid[number - 1][1]
                    if number - 1 < len(notes_grid) and len(notes_grid[number - 1]) > 1 else "",
                ) for number in range(27, 35)
            }
            summary_values = _batch_summary_values(batch_summary, version)
            notes_xml = by_part[notes_part].decode("utf-8")
            by_part[notes_part] = _patch_batch_summary_xml(
                notes_xml, summary_values, region_values=region_values).encode("utf-8")

        destination.parent.mkdir(parents=True, exist_ok=True)
        self._commit(destination, entries, by_part, expected_by_part,
                     expected_cleared_by_part)
        return destination

    def _commit(self, destination: Path, entries, by_part: dict[str, bytes],
                expected_by_part: dict[str, dict[str, str | None]],
                expected_cleared_by_part: dict[str, tuple[str, ...]]) -> None:
        temporary = destination.with_name(
            f".{destination.name}.{uuid.uuid4().hex}{_TEMP_SUFFIX}")
        original_by_name = {info.filename: data for info, data in entries}
        try:
            with ZipFile(temporary, "w", ZIP_DEFLATED) as target:
                for info, data in entries:
                    target.writestr(info, by_part.get(info.filename, data))
            with ZipFile(temporary) as archive:
                if archive.namelist() != [info.filename for info, _ in entries]:
                    raise ResultWorkbookWriteError(
                        "结果工作簿部件列表与输入不一致，拒绝提交")
                for name in archive.namelist():
                    data = archive.read(name)
                    if name not in by_part and data != original_by_name[name]:
                        raise ResultWorkbookWriteError(
                            f"非目标ZIP部件被改写：{name}")
                for part, expected in expected_by_part.items():
                    xml = archive.read(part).decode("utf-8")
                    assert_unique_references(xml)
                    assert_result_payloads(xml, expected)
                    _assert_result_cells_cleared(
                        xml, expected_cleared_by_part.get(part, ()))
            os.replace(temporary, destination)
        except BaseException:
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                pass
            raise
