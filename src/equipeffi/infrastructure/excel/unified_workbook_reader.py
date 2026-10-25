"""统一V6/V6.1/V6.2工作簿Reader；只读正式输入列，不解释标准阈值。"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from ...application.ports.batch_workbook import BatchSourceRow, BatchSourceWorkbook
from ...application.ports.unified_workbook import (
    UnifiedSourceWorkbook,
    UnifiedWorkbookReader as UnifiedWorkbookReaderPort,
)
from ...domain.devices.transformer.input_contract import (
    TRANSFORMER_CATEGORIES,
    condition_options,
)
from ...domain.devices.motor.input_contract import (
    MOTOR_CATEGORIES,
)
from .ooxml_reader import OOXMLReadError, OOXMLWorkbook
from .pump_workbook_reader import V6PumpWorkbookReader
from .template_resource import (
    MOTOR_SHEET_CONTRACT,
    TEMPLATE_MANIFEST,
    TRANSFORMER_SHEET_CONTRACT,
    validate_v6_template,
)

TRANSFORMER_SHEET = str(TRANSFORMER_SHEET_CONTRACT["sheet_name"])
_CATEGORY_BY_LABEL = {item.label: item for item in TRANSFORMER_CATEGORIES}
_CATEGORY_BY_ID = {item.category_id: item for item in TRANSFORMER_CATEGORIES}
_MOTOR_CATEGORY_BY_LABEL = {item.label: item for item in MOTOR_CATEGORIES}
_NON_DEVICE_SHEET_IDS = {"configuration", "instructions", "template_notes"}
_TRANSFORMER_INPUT_FIELDS = {
    str(field["column"]): field
    for field in TRANSFORMER_SHEET_CONTRACT["fields"]
    if field.get("role") == "input"
}
_MOTOR_INPUT_FIELDS = {
    str(field["column"]): field
    for field in MOTOR_SHEET_CONTRACT["fields"]
    if field.get("role") == "input"
}
_DATE_SENSITIVE_INPUT_COLUMNS = frozenset({
    "D", "F", "G", "H", "I", "J", "K", "V", "W", "X", "Y",
})
_MOTOR_DATE_SENSITIVE_INPUT_COLUMNS = frozenset({"D", "F", "G", "H", "I", "J", "K", "L", "M"})


def _column_index(letters: str) -> int:
    value = 0
    for char in letters.upper():
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def _cell(row: list[Any], column: str) -> Any:
    index = _column_index(column)
    if index >= len(row):
        return ""
    value = row[index]
    return "" if value is None else value


def _is_blank(values: dict[str, Any]) -> bool:
    return not any(value not in (None, "") for value in values.values())


def _transformer_values(row: list[Any]) -> dict[str, Any]:
    category_label = _cell(row, "F")
    category = _CATEGORY_BY_LABEL.get(str(category_label)) if category_label else None
    category_id = category.category_id if category else category_label
    raw_condition = _cell(row, "H")
    standard_conditions = raw_condition
    if category is not None and raw_condition not in (None, ""):
        option = next((item for item in condition_options(category.category_id)
                       if item.label == str(raw_condition)), None)
        if option is not None:
            standard_conditions = option.condition_id

    values: dict[str, Any] = {
        "device_name": _cell(row, "B"),
        "model": _cell(row, "C"),
        "quantity": _cell(row, "D"),
        "location": _cell(row, "E"),
        "category_id": category_id,
        "capacity_kva": _cell(row, "G"),
        "standard_conditions": standard_conditions,
        "no_load_loss_w": _cell(row, "J"),
        "load_loss_w": _cell(row, "K"),
        "photo": _cell(row, "S"),
        "fill_note": _cell(row, "T"),
        "hv_rated_voltage_kv": _cell(row, "V"),
        "lv_rated_voltage_kv": _cell(row, "W"),
        "uk_hl_rated_percent": _cell(row, "X"),
        "uk_ml_rated_percent": _cell(row, "Y"),
    }
    impedance = _cell(row, "I")
    if category is not None and category.table_no in {23, 24, 27, 28}:
        values["uk_hm_rated_percent"] = impedance
    else:
        values["uk_rated_percent"] = impedance
    return values


def _value_key_for_column(column: str, values: dict[str, Any]) -> str | None:
    field = _TRANSFORMER_INPUT_FIELDS.get(column)
    if field is None:
        return None
    if column != "I":
        return str(field.get("field_id") or "") or None
    category = _CATEGORY_BY_ID.get(str(values.get("category_id", "")))
    if category is not None and category.table_no in {23, 24, 27, 28}:
        return "uk_hm_rated_percent"
    return "uk_rated_percent"


def _source_input_errors_by_row(cell_metadata) -> dict[int, tuple[tuple[str, str], ...]]:
    grouped: dict[int, list[tuple[str, str]]] = {}
    for reference, metadata in cell_metadata.items():
        match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", reference)
        if match is None:
            continue
        column = match.group(1)
        row_number = int(match.group(2))
        field = _TRANSFORMER_INPUT_FIELDS.get(column)
        if field is None:
            continue
        label = str(field.get("label") or column)
        address = f"{column}{row_number}（{label}）"
        if metadata.has_formula:
            grouped.setdefault(row_number, []).append(
                (column, f"{address}含有公式，请填写固定输入值后重试。"))
        if metadata.cell_type == "e":
            detail = f"（{metadata.raw_value}）" if metadata.raw_value else ""
            grouped.setdefault(row_number, []).append(
                (column, f"{address}含有Excel错误值{detail}，请修正后重试。"))
        if (metadata.is_date and column in _DATE_SENSITIVE_INPUT_COLUMNS
                and metadata.raw_value != ""):
            grouped.setdefault(row_number, []).append(
                (column, f"{address}被识别为日期或时间格式，请填写固定业务值后重试。"))
    return {row: tuple(errors) for row, errors in grouped.items()}


def _motor_values(row: list[Any]) -> dict[str, Any]:
    raw_category = _cell(row, "F")
    category = _MOTOR_CATEGORY_BY_LABEL.get(str(raw_category)) if raw_category else None
    category_id = category.category_id if category else raw_category

    raw_basis = _cell(row, "I")

    return {
        "device_name": _cell(row, "B"),
        "model": _cell(row, "C"),
        "quantity": _cell(row, "D"),
        "location": _cell(row, "E"),
        "category_id": category_id,
        "rated_voltage_kv": _cell(row, "G"),
        "rated_frequency_hz": _cell(row, "H"),
        # Preserve the selected display label; Domain input_contract performs
        # the controlled-label to stable-status conversion and records the raw.
        "efficiency_basis_status": raw_basis,
        "efficiency_basis_raw": raw_basis,
        "rated_output_power_kw": _cell(row, "J"),
        # H and K are passed through unchanged. The Application contract owns
        # frequency scope and positive-even pole validation/table coverage.
        "poles": _cell(row, "K"),
        "max_nameplate_speed_rpm": _cell(row, "L"),
        "measured_efficiency_pct": _cell(row, "M"),
        "photo": _cell(row, "R"),
        "user_note": _cell(row, "S"),
    }


def _motor_source_input_errors_by_row(cell_metadata) -> dict[int, tuple[tuple[str, str], ...]]:
    grouped: dict[int, list[tuple[str, str]]] = {}
    for reference, metadata in cell_metadata.items():
        match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", reference)
        if match is None:
            continue
        column = match.group(1)
        row_number = int(match.group(2))
        field = _MOTOR_INPUT_FIELDS.get(column)
        if field is None:
            continue
        label = str(field.get("label") or column)
        address = f"{column}{row_number}（{label}）"
        if metadata.has_formula:
            grouped.setdefault(row_number, []).append(
                (column, f"{address}含有公式，请填写固定输入值后重试。"))
        if metadata.cell_type == "e":
            detail = f"（{metadata.raw_value}）" if metadata.raw_value else ""
            grouped.setdefault(row_number, []).append(
                (column, f"{address}含有Excel错误值{detail}，请修正后重试。"))
        if (metadata.is_date and column in _MOTOR_DATE_SENSITIVE_INPUT_COLUMNS
                and metadata.raw_value != ""):
            grouped.setdefault(row_number, []).append(
                (column, f"{address}被识别为日期或时间格式，请填写固定业务值后重试。"))
        if (column == "M" and metadata.is_percentage
                and metadata.raw_value != ""):
            grouped.setdefault(row_number, []).append((
                column,
                f"{address}使用了百分比单元格格式，请取消该格式并按普通数值填写"
                "（例如90，不要输入90%）。"))
    return {row: tuple(errors) for row, errors in grouped.items()}


def _motor_value_key_for_column(column: str) -> tuple[str, ...]:
    field = _MOTOR_INPUT_FIELDS.get(column)
    if field is None:
        return ()
    key = str(field.get("field_id") or "")
    if not key:
        return ()
    if column == "I":
        return ("efficiency_basis_status", "efficiency_basis_raw")
    return (key,)


class TransformerWorkbookReader:
    """读取已登记统一模板的「变压器」Sheet为Application批量输入行。"""

    def read(self, source: Path, *, template_identity: dict[str, str] | None = None
             ) -> BatchSourceWorkbook:
        source = Path(source)
        validation = validate_v6_template(source, check_pump_sheet=False)
        if not validation.is_valid:
            raise OOXMLReadError(validation.message)
        if validation.identity.get("template_version") not in {"V6.1", "V6.2"}:
            raise OOXMLReadError("当前工作簿的变压器Sheet尚未接入；请使用V6.1或V6.2模板")

        contract = TRANSFORMER_SHEET_CONTRACT
        input_columns = set(_TRANSFORMER_INPUT_FIELDS)
        with OOXMLWorkbook(source) as workbook:
            grid = workbook.rows(TRANSFORMER_SHEET)
            cell_metadata = workbook.cell_metadata(
                TRANSFORMER_SHEET, columns=input_columns)
        source_errors_by_row = _source_input_errors_by_row(cell_metadata)
        header_index = int(contract["header_row"]) - 1
        if header_index < 0 or header_index >= len(grid):
            raise OOXMLReadError("「变压器」Sheet缺少正式表头行")
        # V61TransformerTemplateResource已对整行表头按Manifest逐列核对。

        rows: list[BatchSourceRow] = []
        blank = 0
        for row_number, raw in enumerate(grid[header_index + 1:],
                                         start=header_index + 2):
            values = _transformer_values(raw)
            source_errors = source_errors_by_row.get(row_number, ())
            for column, _message in source_errors:
                key = _value_key_for_column(column, values)
                if key is not None:
                    values[key] = ""
            if _is_blank(values) and not source_errors:
                blank += 1
                continue
            rows.append(BatchSourceRow(
                row_number=row_number, values=values,
                input_errors=tuple(message for _column, message in source_errors)))

        identity = dict(template_identity or validation.identity or {})
        identity.update({
            "sheet_id": str(contract["sheet_id"]),
            "sheet_contract_revision": str(contract["contract_revision"]),
        })
        if validation.identity_source:
            identity["identity_source"] = validation.identity_source
        return BatchSourceWorkbook(
            path=str(source), rows=tuple(rows), skipped_blank_rows=blank,
            template_identity=identity)


class MotorWorkbookReader:
    """读取V6.2「电动机」输入，不根据型号或残留列推断类别。"""

    def read(self, source: Path, *, template_identity: dict[str, str] | None = None
             ) -> BatchSourceWorkbook:
        source = Path(source)
        validation = validate_v6_template(source, check_pump_sheet=False)
        if not validation.is_valid:
            raise OOXMLReadError(validation.message)
        if validation.identity.get("template_version") != "V6.2":
            raise OOXMLReadError("电动机Sheet仅在V6.2模板中接通")

        contract = MOTOR_SHEET_CONTRACT
        input_columns = set(_MOTOR_INPUT_FIELDS)
        with OOXMLWorkbook(source) as workbook:
            grid = workbook.rows(str(contract["sheet_name"]))
            cell_metadata = workbook.cell_metadata(
                str(contract["sheet_name"]), columns=input_columns)
        source_errors_by_row = _motor_source_input_errors_by_row(cell_metadata)
        header_index = int(contract["header_row"]) - 1
        if header_index < 0 or header_index >= len(grid):
            raise OOXMLReadError("「电动机」Sheet缺少正式表头行")

        rows: list[BatchSourceRow] = []
        blank = 0
        for row_number, raw in enumerate(grid[header_index + 1:],
                                         start=header_index + 2):
            values = _motor_values(raw)
            source_errors = source_errors_by_row.get(row_number, ())
            for column, _message in source_errors:
                for key in _motor_value_key_for_column(column):
                    values[key] = ""
            if _is_blank(values) and not source_errors:
                blank += 1
                continue
            rows.append(BatchSourceRow(
                row_number=row_number, values=values,
                input_errors=tuple(message for _column, message in source_errors)))

        identity = dict(template_identity or validation.identity or {})
        identity.update({
            "sheet_id": str(contract["sheet_id"]),
            "sheet_contract_revision": str(contract["contract_revision"]),
        })
        if validation.identity_source:
            identity["identity_source"] = validation.identity_source
        return BatchSourceWorkbook(
            path=str(source), rows=tuple(rows), skipped_blank_rows=blank,
            template_identity=identity)


class UnifiedWorkbookReader(UnifiedWorkbookReaderPort):
    """按模板Manifest同时读取已接通Sheet，并列明保留未处理Sheet。"""

    def __init__(self, *, pump_reader: V6PumpWorkbookReader | None = None,
                 transformer_reader: TransformerWorkbookReader | None = None,
                 motor_reader: MotorWorkbookReader | None = None):
        self._pump_reader = pump_reader or V6PumpWorkbookReader()
        self._transformer_reader = transformer_reader or TransformerWorkbookReader()
        self._motor_reader = motor_reader or MotorWorkbookReader()

    def read(self, source: Path) -> UnifiedSourceWorkbook:
        source = Path(source)
        validation = validate_v6_template(source, check_pump_sheet=False)
        if not validation.is_valid:
            raise OOXMLReadError(validation.message)
        identity = dict(validation.identity or {})
        version = identity.get("template_version")
        entry = next((item for item in TEMPLATE_MANIFEST["templates"]
                      if item.get("template_id") == identity.get("template_id")
                      and item.get("template_version") == version), None)
        if entry is None:
            raise OOXMLReadError("工作簿模板身份未在Manifest登记")

        sheets: dict[str, BatchSourceWorkbook] = {}
        unprocessed: list[str] = []
        for sheet in entry.get("sheets", ()):
            name = str(sheet.get("sheet_name", ""))
            if sheet.get("status") != "CONNECTED":
                if (name in validation.sheet_names
                        and sheet.get("sheet_id") not in _NON_DEVICE_SHEET_IDS):
                    unprocessed.append(name)
                continue
            if sheet.get("sheet_id") == "centrifugal_pump":
                sheets[name] = self._pump_reader.read(source)
            elif sheet.get("sheet_id") == "transformer":
                sheets[name] = self._transformer_reader.read(
                    source, template_identity=identity)
            elif sheet.get("sheet_id") == "motor":
                sheets[name] = self._motor_reader.read(
                    source, template_identity=identity)
        if not sheets:
            raise OOXMLReadError("工作簿没有可评价的已接通Sheet")
        return UnifiedSourceWorkbook(
            path=str(source), sheets=sheets, template_identity=identity,
            unprocessed_sheets=tuple(unprocessed))
