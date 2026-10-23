"""一次ZIP补丁写出泵与变压器结果，保留所有输入和非目标OOXML部件。"""
from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
import uuid
from zipfile import ZIP_DEFLATED, ZipFile

from ...application.ports.batch_workbook import BatchRowOutcome
from .pump_result_writer import (
    ResultWorkbookExistsError,
    ResultWorkbookWriteError,
    _as_number,
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
from .template_resource import (
    PUMP_SHEET,
    TEMPLATE_MANIFEST,
    TRANSFORMER_SHEET_CONTRACT,
    V61TransformerTemplateResource,
)
from .worksheet_patch import SheetStructureError, WorksheetPatch


TRANSFORMER_SHEET = str(TRANSFORMER_SHEET_CONTRACT["sheet_name"])
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
if (len(_TRANSFORMER_THRESHOLD_FIELDS) != 6
        or set(_TRANSFORMER_RESULT_BY_KEY) != {"conclusion", "messages"}):
    raise RuntimeError("变压器模板清单的结果字段契约不完整")
_TEMP_SUFFIX = ".equipeffi-tmp"


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


class UnifiedResultWorkbookWriter:
    """在同一个ZIP重写周期内补丁所有已接通Sheet，并原子提交新工作簿。"""

    def default_destination(self, source: Path) -> Path:
        source = Path(source)
        return source.with_name(default_result_filename(source))

    def write(self, source: Path,
              outcomes_by_sheet: dict[str, dict[int, BatchRowOutcome]],
              destination: Path, *, overwrite: bool = False) -> Path:
        source = Path(source)
        destination = Path(destination)
        if source.resolve() == destination.resolve():
            raise ValueError("结果工作簿不得覆盖原始输入文件")
        if destination.exists() and not overwrite:
            raise ResultWorkbookExistsError(
                f"结果工作簿已存在，不得静默覆盖：{destination}")

        validation = V61TransformerTemplateResource().validate(
            source, check_pump_sheet=False)
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
        for name, outcomes in outcomes_by_sheet.items():
            contract = sheet_contracts[name]
            if outcomes and contract.get("status") != "CONNECTED":
                raise ResultWorkbookWriteError(f"工作表「{name}」尚未接通，不能写入结果")
            if outcomes and contract.get("sheet_id") not in {
                    "centrifugal_pump", "transformer"}:
                raise ResultWorkbookWriteError(f"工作表「{name}」没有结果写入适配器")
            if outcomes:
                selected[name] = outcomes

        destination.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(source) as archive:
            entries = [(info, archive.read(info.filename))
                       for info in archive.infolist()]
            names = [info.filename for info, _ in entries]
            if len(names) != len(set(names)):
                raise ResultWorkbookWriteError("输入工作簿包含重复ZIP部件名称")
            targets = {name: _sheet_target(archive, name) for name in selected}

        for name, target in targets.items():
            if not target or target not in names:
                raise ResultWorkbookWriteError(f"工作簿中找不到结果目标Sheet：{name}")

        by_part = {info.filename: data for info, data in entries}
        expected_by_part: dict[str, dict[str, str | None]] = {}
        for name, outcomes in selected.items():
            part = targets[name]
            source_xml = by_part[part].decode("utf-8")
            if name == PUMP_SHEET:
                result_xml = patch_pump_sheet_xml(source_xml, outcomes)
                result_columns = tuple(
                    field["column"] for field in next(
                        sheet for sheet in entry["sheets"]
                        if sheet.get("sheet_id") == "centrifugal_pump")["fields"]
                    if field.get("role") == "result")
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
            else:
                raise ResultWorkbookWriteError(f"没有工作表「{name}」的结果写入适配器")
            try:
                assert_input_preserved(
                    source_xml, result_xml,
                    result_columns=result_columns,
                    row_numbers={int(number) for number in outcomes})
                assert_result_payloads(result_xml, expected)
            except InvariantViolation as error:
                raise ResultWorkbookWriteError(
                    f"「{name}」结果写回独立校验失败：{error}") from error
            by_part[part] = result_xml.encode("utf-8")
            expected_by_part[part] = expected

        self._commit(destination, entries, by_part, expected_by_part)
        return destination

    def _commit(self, destination: Path, entries, by_part: dict[str, bytes],
                expected_by_part: dict[str, dict[str, str | None]]) -> None:
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
            os.replace(temporary, destination)
        except BaseException:
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                pass
            raise
