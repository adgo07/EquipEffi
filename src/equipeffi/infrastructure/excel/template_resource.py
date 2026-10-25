from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib.resources as resources
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from ...domain.devices.motor.input_contract import (
    BASIS_OPTIONS as MOTOR_BASIS_OPTIONS,
    MOTOR_CATEGORIES,
    scope_hint as motor_scope_hint,
    efficiency_basis_hint as motor_efficiency_basis_hint,
    visible_fields as motor_visible_fields,
)
from .ooxml_reader import OOXMLReadError, OOXMLWorkbook


MANIFEST_FILENAME = "TEMPLATE_MANIFEST.json"


def _read_manifest() -> dict[str, Any]:
    """Read the one packaged template release manifest."""

    filesystem_path = Path(__file__).resolve().parents[2] / "resources" / MANIFEST_FILENAME
    if filesystem_path.is_file():
        return json.loads(filesystem_path.read_text(encoding="utf-8"))
    try:
        packaged = resources.files("equipeffi").joinpath("resources", MANIFEST_FILENAME)
        return json.loads(packaged.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise RuntimeError(f"未能读取随包分发的模板清单：{MANIFEST_FILENAME}") from exc


TEMPLATE_MANIFEST = _read_manifest()
LEGACY_V6_TEMPLATE_VERSION = "V6-20261005"
V6_TEMPLATE_ENTRY: dict[str, Any] = next(
    entry for entry in TEMPLATE_MANIFEST["templates"]
    if entry.get("template_id") == TEMPLATE_MANIFEST["formal_windows_v1_template"]
    and entry.get("template_version") == LEGACY_V6_TEMPLATE_VERSION
    and entry.get("status") == "FORMAL"
)
V6_TEMPLATE_IDENTITY: dict[str, str] = {
    "template_id": V6_TEMPLATE_ENTRY["template_id"],
    "template_version": V6_TEMPLATE_ENTRY["template_version"],
    "template_kind": V6_TEMPLATE_ENTRY["template_kind"],
    "filename": V6_TEMPLATE_ENTRY["filename"],
    "source_filename": V6_TEMPLATE_ENTRY["source_filename"],
    "source_sha256": V6_TEMPLATE_ENTRY["source_sha256"],
    "asset_sha256": V6_TEMPLATE_ENTRY["asset_sha256"],
    "generated_by": TEMPLATE_MANIFEST["generated_by"],
    "authorized_modification": V6_TEMPLATE_ENTRY["authorized_modification"]["sheet"],
    "provenance": V6_TEMPLATE_ENTRY["source_provenance"],
    "template_contract_revision": V6_TEMPLATE_ENTRY["template_contract_revision"],
}
DEFAULT_V6_TEMPLATE = V6_TEMPLATE_IDENTITY["filename"]
REQUIRED_V6_SHEETS: tuple[str, ...] = tuple(
    sheet["sheet_name"] for sheet in V6_TEMPLATE_ENTRY["sheets"]
)

# V6.1 is an explicitly selected candidate template. Keep the legacy V6 default
# stable until the product integration and acceptance work is complete.
V61_TEMPLATE_ENTRY: dict[str, Any] = next(
    entry for entry in TEMPLATE_MANIFEST["templates"]
    if entry.get("template_id") == V6_TEMPLATE_IDENTITY["template_id"]
    and entry.get("template_version") == "V6.1"
)
V61_TEMPLATE_IDENTITY: dict[str, str] = {
    "template_id": str(V61_TEMPLATE_ENTRY["template_id"]),
    "template_version": str(V61_TEMPLATE_ENTRY["template_version"]),
    "template_kind": str(V61_TEMPLATE_ENTRY.get("template_kind", "")),
    "template_contract_revision": str(
        V61_TEMPLATE_ENTRY.get("template_contract_revision", "")),
    "filename": str(V61_TEMPLATE_ENTRY.get("filename", "")),
    "asset_sha256": str(V61_TEMPLATE_ENTRY.get("asset_sha256", "")),
    "source_filename": str(V61_TEMPLATE_ENTRY.get("source_filename", "")),
    "source_sha256": str(V61_TEMPLATE_ENTRY.get("source_sha256", "")),
    "source_provenance": str(V61_TEMPLATE_ENTRY.get("source_provenance", "")),
}
DEFAULT_V61_TEMPLATE = V61_TEMPLATE_IDENTITY["filename"]
REQUIRED_V61_SHEETS: tuple[str, ...] = tuple(
    sheet["sheet_name"] for sheet in V61_TEMPLATE_ENTRY["sheets"]
)
V62_TEMPLATE_ID = "equipeffi.device-efficiency.V6.2"
V62_TEMPLATE_ENTRY: dict[str, Any] = next(
    entry for entry in TEMPLATE_MANIFEST["templates"]
    if entry.get("template_version") == "V6.2"
)
if V62_TEMPLATE_ENTRY.get("template_id") != V62_TEMPLATE_ID:
    raise RuntimeError("V6.2模板身份必须使用独立template_id")
V62_TEMPLATE_IDENTITY: dict[str, str] = {
    "template_id": str(V62_TEMPLATE_ENTRY["template_id"]),
    "template_version": str(V62_TEMPLATE_ENTRY["template_version"]),
    "template_kind": str(V62_TEMPLATE_ENTRY.get("template_kind", "")),
    "template_contract_revision": str(
        V62_TEMPLATE_ENTRY.get("template_contract_revision", "")),
    "filename": str(V62_TEMPLATE_ENTRY.get("filename", "")),
    "asset_sha256": str(V62_TEMPLATE_ENTRY.get("asset_sha256", "")),
    "source_filename": str(V62_TEMPLATE_ENTRY.get("source_filename", "")),
    "source_sha256": str(V62_TEMPLATE_ENTRY.get("source_sha256", "")),
    "source_provenance": str(V62_TEMPLATE_ENTRY.get("source_provenance", "")),
}
DEFAULT_V62_TEMPLATE = V62_TEMPLATE_IDENTITY["filename"]
REQUIRED_V62_SHEETS: tuple[str, ...] = tuple(
    sheet["sheet_name"] for sheet in V62_TEMPLATE_ENTRY["sheets"]
)
MOTOR_SHEET_CONTRACT: dict[str, Any] = next(
    sheet for sheet in V62_TEMPLATE_ENTRY["sheets"]
    if sheet.get("sheet_id") == "motor")
PUMP_SHEET_CONTRACT: dict[str, Any] = next(
    sheet for sheet in V6_TEMPLATE_ENTRY["sheets"]
    if sheet.get("sheet_id") == "centrifugal_pump"
)
PUMP_SHEET = PUMP_SHEET_CONTRACT["sheet_name"]
CONFIG_SHEET = next(
    sheet["sheet_name"] for sheet in V6_TEMPLATE_ENTRY["sheets"]
    if sheet.get("sheet_id") == "configuration"
)
CONFIGURATION_CONTRACT: dict[str, Any] = V6_TEMPLATE_ENTRY["configuration_contract"]
CONFIG_TABLE = CONFIGURATION_CONTRACT["field_dictionary_table"]
TRANSFORMER_SHEET_CONTRACT: dict[str, Any] = next(
    sheet for sheet in V61_TEMPLATE_ENTRY["sheets"]
    if sheet.get("sheet_id") == "transformer")


def input_field_columns(contract: dict[str, Any] | None = None) -> tuple[tuple[str, str], ...]:
    selected = contract or PUMP_SHEET_CONTRACT
    return tuple((field["column"], field["field_id"])
                 for field in selected["fields"]
                 if field.get("role") == "input" and field.get("field_id"))


def _column_index(letter: str) -> int:
    value = 0
    for char in letter.upper():
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def _cell_position(reference: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"\$?([A-Z]{1,3})\$?([1-9]\d*)",
                         str(reference).strip().upper())
    if match is None:
        return None
    return _column_index(match.group(1)), int(match.group(2))


def sheet_data_layout_issues(
        merged_ranges: tuple[str, ...] | list[str],
        contract: dict[str, Any]) -> tuple[str, ...]:
    """Reject data-area merges that obscure a connected sheet's I/O cells.

    The data area is intentionally unbounded: Table size is not a Reader capacity
    limit, and a missing Table alone does not make an otherwise compatible sheet
    invalid.
    """

    selected = contract
    sheet_name = str(selected.get("sheet_name") or "工作表")
    first_data_row = int(selected["header_row"]) + 1
    fields = [field for field in selected["fields"]
              if field.get("role") in {"input", "result"}]
    affected_columns = {
        _column_index(str(field["column"])): str(field["column"])
        for field in fields
    }
    issues: list[str] = []
    for reference in merged_ranges:
        parts = str(reference).split(":")
        if len(parts) != 2:
            issues.append(f"{sheet_name}数据区合并范围格式无效：{reference!r}")
            continue
        start = _cell_position(parts[0])
        end = _cell_position(parts[1])
        if start is None or end is None:
            issues.append(f"{sheet_name}数据区合并范围格式无效：{reference!r}")
            continue
        min_column, max_column = sorted((start[0], end[0]))
        max_row = max(start[1], end[1])
        if max_row < first_data_row:
            continue
        covered_columns = [
            column for index, column in sorted(affected_columns.items())
            if min_column <= index <= max_column
        ]
        if covered_columns:
            issues.append(
                f"{sheet_name}数据区合并范围 {reference} 覆盖输入/结果列 "
                f"{'、'.join(covered_columns)}（第 {first_data_row} 行起不允许合并）")
    return tuple(issues)


def pump_data_layout_issues(
        merged_ranges: tuple[str, ...] | list[str],
        contract: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Compatibility entry point for the established pump reader and checks."""

    return sheet_data_layout_issues(merged_ranges, contract or PUMP_SHEET_CONTRACT)


def _header_parts(value: Any) -> tuple[str, str, tuple[str, ...]]:
    text = str(value or "").replace("\r", "").strip()
    parts = tuple(part.strip() for part in text.split("\n"))
    label = parts[0] if parts else ""
    unit = parts[1] if len(parts) > 1 else ""
    if (len(unit) >= 2 and unit[0] == "(" and unit[-1] == ")"
            and unit[1:-1].strip()):
        unit = unit[1:-1].strip()
    return label, unit, parts[2:]


def pump_header_issues(header: list[Any], contract: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Compare exact pump header labels and units with the selected sheet contract."""

    selected = contract or PUMP_SHEET_CONTRACT
    issues: list[str] = []
    for field in selected["fields"]:
        column = field["column"]
        index = _column_index(column)
        value = header[index] if index < len(header) else ""
        label, unit, extra = _header_parts(value)
        expected_label = str(field.get("label") or "")
        expected_unit = str(field.get("unit") or "")
        if label != expected_label or unit != expected_unit or extra:
            actual = label + (f" ({unit})" if unit else "")
            expected = expected_label + (f" ({expected_unit})" if expected_unit else "")
            issues.append(f"{column} 列期望「{expected}」，实际为「{actual}」")
    return tuple(issues)
class TemplateResourceError(ValueError):
    """模板资源不存在、损坏或结构不符合模板契约。"""


@dataclass(frozen=True)
class TemplateValidationResult:
    path: str
    sha256: str
    sheet_names: tuple[str, ...]
    missing_sheets: tuple[str, ...]
    is_valid: bool
    message: str
    identity: dict[str, str] | None = None
    sheet_contracts: dict[str, str] | None = None
    identity_source: str = ""
    pump_sheet_contract: dict[str, Any] | None = None
    issues: tuple[str, ...] = ()


def _version_mismatch(base: TemplateValidationResult,
                      expected_version: str) -> TemplateValidationResult:
    actual = (base.identity or {}).get("template_version", "")
    issue = (f"模板版本不匹配：资源要求{expected_version}，实际为{actual or '未知'}")
    issues = tuple(base.issues) + (issue,)
    return TemplateValidationResult(
        path=base.path, sha256=base.sha256, sheet_names=base.sheet_names,
        missing_sheets=base.missing_sheets, is_valid=False,
        message=f"模板不兼容：{issue}", identity=base.identity,
        sheet_contracts=base.sheet_contracts,
        identity_source=base.identity_source,
        pump_sheet_contract=base.pump_sheet_contract,
        issues=issues)


def _workbook_sheet_names(path: Path) -> tuple[str, ...]:
    try:
        with ZipFile(path) as archive:
            xml = archive.read("xl/workbook.xml")
    except (BadZipFile, KeyError, OSError) as exc:
        raise TemplateResourceError(f"无法读取Excel工作簿结构：{exc}") from exc
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise TemplateResourceError(f"Excel工作簿结构XML无效：{exc}") from exc
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return tuple(str(node.attrib.get("name", "")) for node in root.findall("main:sheets/main:sheet", namespace) if node.attrib.get("name"))


def _workbook_defined_names(path: Path) -> dict[str, tuple[str, ...]]:
    try:
        with ZipFile(path) as archive:
            xml = archive.read("xl/workbook.xml")
        root = ElementTree.fromstring(xml)
    except (BadZipFile, KeyError, OSError, ElementTree.ParseError) as exc:
        raise TemplateResourceError(f"无法读取Excel模板身份标记：{exc}") from exc
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values: dict[str, list[str]] = {}
    for node in root.findall("main:definedNames/main:definedName", namespace):
        name = str(node.attrib.get("name", ""))
        # Identity markers are workbook-scoped. Local names must not shadow them.
        if name and "localSheetId" not in node.attrib:
            values.setdefault(name, []).append(node.text or "")
    return {name: tuple(items) for name, items in values.items()}


def _defined_name_expressions(path: Path) -> dict[str, tuple[str, ...]]:
    """Return raw workbook-scoped name expressions for contract checks."""
    try:
        with ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    except (BadZipFile, KeyError, OSError, ElementTree.ParseError) as exc:
        raise TemplateResourceError(f"无法读取Excel命名范围：{exc}") from exc
    values: dict[str, list[str]] = {}
    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    for node in root.findall(f"{{{namespace}}}definedNames/{{{namespace}}}definedName"):
        name = str(node.attrib.get("name", ""))
        if name and "localSheetId" not in node.attrib:
            values.setdefault(name, []).append(node.text or "")
    return {name: tuple(items) for name, items in values.items()}


def _motor_config_issues(path: Path, contract_entry: dict[str, Any]) -> list[str]:
    """Mechanically compare V6.2's dedicated config area to Domain input contract."""
    configuration = contract_entry.get("configuration_contract", {})
    category_cfg = configuration.get("motor_category_enum", {})
    basis_cfg = configuration.get("motor_efficiency_basis_enum", {})
    excel_validation_cfg = configuration.get("motor_excel_validations", {})
    try:
        with OOXMLWorkbook(path) as workbook:
            rows = workbook.rows(str(next(
                sheet["sheet_name"] for sheet in contract_entry["sheets"]
                if sheet.get("sheet_id") == "configuration")))
        names = _defined_name_expressions(path)
    except (OOXMLReadError, TemplateResourceError, KeyError, StopIteration) as exc:
        return [f"无法核对电动机配置契约：{exc}"]

    issues: list[str] = []

    def col_index(column: str) -> int:
        return _column_index(str(column))

    def cell(column: str, row_number: int) -> Any:
        row_index = row_number - 1
        col = col_index(column)
        return rows[row_index][col] if row_index < len(rows) and col < len(rows[row_index]) else ""

    categories = tuple(MOTOR_CATEGORIES)
    motor_contract = next((sheet for sheet in contract_entry.get("sheets", ())
                           if sheet.get("sheet_id") == "motor"), {})
    field_validations = {
        str(field.get("field_id")): field.get("excel_validation")
        for field in motor_contract.get("fields", ())
        if field.get("field_id") and field.get("excel_validation")
    }
    if excel_validation_cfg != field_validations:
        issues.append("Manifest电动机字段校验与电机专属模板配置不一致")

    first_row = int(category_cfg.get("first_row", 2))
    label_col = str(category_cfg.get("column", "EW"))
    id_col = str(category_cfg.get("category_ids_column", "EX"))
    for offset, category in enumerate(categories):
        row_number = first_row + offset
        if cell(label_col, row_number) != category.label:
            issues.append(f"配置!{label_col}{row_number}类别名称与Domain契约不一致")
        if cell(id_col, row_number) != category.category_id:
            issues.append(f"配置!{id_col}{row_number}类别ID与Domain契约不一致")
    for column in (label_col, id_col):
        if any(cell(column, row_number) not in (None, "")
               for row_number in range(first_row + len(categories), len(rows) + 1)):
            issues.append(f"配置!{column}含有Domain之外的电动机类别选项")

    basis_first_row = int(basis_cfg.get("first_row", 2))
    basis_col = str(basis_cfg.get("column", "FG"))
    expected_basis = tuple(label for _code, label in MOTOR_BASIS_OPTIONS)
    actual_basis = tuple(
        value for row_number in range(basis_first_row, len(rows) + 1)
        if (value := cell(basis_col, row_number)) not in (None, ""))
    if actual_basis != expected_basis:
        issues.append(f"配置!{basis_col}效率口径选项与Domain契约不一致")

    expected_names: dict[str, str] = {
        str(category_cfg.get("defined_name", "")):
        f"'配置'!${label_col}${first_row}:${label_col}${first_row + len(categories) - 1}",
        str(category_cfg.get("category_ids_defined_name", "")):
        f"'配置'!${id_col}${first_row}:${id_col}${first_row + len(categories) - 1}",
        str(basis_cfg.get("defined_name", "")):
        f"'配置'!${basis_col}${basis_first_row}:${basis_col}${basis_first_row + len(expected_basis) - 1}",
    }
    for name, expected in expected_names.items():
        expressions = names.get(name, ())
        if len(expressions) != 1 or expressions[0].replace("$", "") != expected.replace("$", ""):
            issues.append(f"电动机专属命名范围 {name} 与配置契约不一致")
    unexpected_motor_names = sorted(
        name for name in names
        if name.startswith("EV_MOTOR_V62_") and name not in expected_names)
    if unexpected_motor_names:
        issues.append("存在Manifest未登记的电动机V6.2命名范围："
                      + "、".join(unexpected_motor_names))
    legacy_motor_names = {
        "EV_MOTOR_CATEGORY", "EV_POLES_LV", "EV_POLES_HV", "EV_POLES_PMSM",
        "EV_MOTOR_VOLTAGE", "EV_COOLING_MOTOR_HV", "EV_COOLING_PMSM",
    }
    retained_legacy = sorted(legacy_motor_names.intersection(names))
    if retained_legacy:
        issues.append("旧电动机定义名仍留在V6.2模板：" + "、".join(retained_legacy))
    return issues


def _motor_manifest_contract_issues(contract: dict[str, Any]) -> list[str]:
    """Check V6.2 field routing and category choices against Domain contract."""
    issues: list[str] = []
    categories = tuple(MOTOR_CATEGORIES)
    expected_ids = [item.category_id for item in categories]
    expected_categories = [
        {"category_id": item.category_id, "label": item.label,
         "table_no": item.table_no}
        for item in categories
    ]
    if contract.get("category_ids") != expected_ids:
        issues.append("Manifest电动机category_ids与Domain类别契约不一致")
    if contract.get("categories") != expected_categories:
        issues.append("Manifest电动机categories与Domain类别契约不一致")

    fields = {
        str(field.get("field_id")): field for field in contract.get("fields", ())
        if field.get("field_id")
    }
    domain_fields: dict[str, Any] = {}
    for category_id in expected_ids:
        for field in motor_visible_fields(category_id):
            domain_fields.setdefault(field.field_id, field)
    for field_id, descriptor in domain_fields.items():
        manifest_field = fields.get(field_id)
        if manifest_field is None:
            issues.append(f"Manifest缺少电动机Domain输入字段：{field_id}")
            continue
        if field_id != "user_note":
            if manifest_field.get("label") != descriptor.label:
                issues.append(f"电动机字段{field_id}标签与Domain契约不一致")
            if manifest_field.get("unit") != descriptor.unit:
                issues.append(f"电动机字段{field_id}单位与Domain契约不一致")
        required_categories = [
            category_id for category_id in expected_ids
            if any(item.field_id == field_id and item.required
                   for item in motor_visible_fields(category_id))
        ]
        if manifest_field.get("required_for_categories") != required_categories:
            issues.append(f"电动机字段{field_id}条件必填与Domain契约不一致")
    if fields.get("poles", {}).get("defined_name_prefix"):
        issues.append("Manifest电动机极数仍声明受控下拉列表")
    return issues


def _transformer_sheet_issues(candidate: Path,
                              contract: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    try:
        with OOXMLWorkbook(candidate) as workbook:
            grid = workbook.rows(str(contract["sheet_name"]))
            merged_ranges = workbook.merged_ranges(str(contract["sheet_name"]))
        issues.extend(sheet_data_layout_issues(merged_ranges, contract))
        header_index = int(contract["header_row"]) - 1
        if header_index < 0 or header_index >= len(grid):
            issues.append("「变压器」Sheet缺少正式表头行")
        else:
            header = grid[header_index]
            for field in contract["fields"]:
                column = str(field["column"])
                index = _column_index(column)
                value = header[index] if index < len(header) else ""
                label, unit, extra = _header_parts(value)
                expected_label = str(field.get("label") or "")
                expected_unit = str(field.get("unit") or "")
                if label != expected_label or unit != expected_unit or extra:
                    expected = expected_label + (f" ({expected_unit})" if expected_unit else "")
                    actual = label + (f" ({unit})" if unit else "")
                    issues.append(f"变压器 {column} 列期望「{expected}」，实际为「{actual}」")
    except (OOXMLReadError, KeyError, TypeError, ValueError) as exc:
        issues.append(f"无法验证变压器 Sheet 契约：{exc}")
    return issues


def _string_name_value(expression: str) -> str | None:
    text = expression.strip()
    if text.startswith("="):
        text = text[1:].strip()
    if len(text) < 2 or text[0] != '"' or text[-1] != '"':
        return None
    return text[1:-1].replace('""', '"')


def _entry_identity(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "template_id": str(entry["template_id"]),
        "template_version": str(entry["template_version"]),
        "template_kind": str(entry.get("template_kind", "")),
        "template_contract_revision": str(entry.get("template_contract_revision", "")),
        "filename": str(entry.get("filename", "")),
        "asset_sha256": str(entry.get("asset_sha256") or ""),
    }


def identity_defined_names(entry: dict[str, Any]) -> dict[str, str]:
    """Workbook-scoped name/value pairs generated from one manifest entry."""

    markers = TEMPLATE_MANIFEST["identity_markers"]
    values = {
        markers["template_id"]: str(entry["template_id"]),
        markers["template_version"]: str(entry["template_version"]),
        markers["template_contract_revision"]: str(entry["template_contract_revision"]),
    }
    for sheet in entry.get("sheets", ()):
        values[f"{markers['sheet_contract_prefix']}{sheet['sheet_id']}"] = str(
            sheet.get("contract_revision") or "")
    return values


def _resolve_v6_identity(path: Path) -> tuple[dict[str, Any] | None, str, tuple[str, ...]]:
    """Resolve an explicit identity, or permit only the registered legacy structure."""

    try:
        names = _workbook_defined_names(path)
    except TemplateResourceError as exc:
        return None, "", (str(exc),)
    return _resolve_v6_identity_from_names(names)


def _resolve_v6_identity_from_names(
        names: dict[str, tuple[str, ...]]) -> tuple[dict[str, Any] | None, str, tuple[str, ...]]:
    markers = TEMPLATE_MANIFEST["identity_markers"]
    marker_names = {
        markers["template_id"],
        markers["template_version"],
        markers["template_contract_revision"],
    }
    prefixed_markers = [name for name in names
                        if name.startswith(markers["sheet_contract_prefix"])]
    present = marker_names.intersection(names)
    has_any_marker = bool(present or prefixed_markers)
    if not has_any_marker:
        legacy_entries = [entry for entry in TEMPLATE_MANIFEST["templates"]
                          if entry.get("legacy_import_compatibility") is True
                          and entry.get("input_compatibility") == "ACCEPTED"]
        if len(legacy_entries) == 1:
            return legacy_entries[0], "legacy-structure", ()
        if len(legacy_entries) > 1:
            return None, "legacy-structure", (
                "存在多个允许的无标记 legacy 版本，必须先按其完整结构唯一识别",)
        return None, "", ("工作簿没有版本标记，且此模板版本不允许 legacy 结构识别",)

    issues: list[str] = []
    if present != marker_names:
        missing = sorted(marker_names - present)
        issues.append("模板身份标记不完整，缺少：" + "、".join(missing))
    values: dict[str, str] = {}
    for name in marker_names:
        items = names.get(name, ())
        if len(items) != 1:
            if len(items) > 1:
                issues.append(f"模板身份标记重复：{name}")
            continue
        parsed = _string_name_value(items[0])
        if parsed is None:
            issues.append(f"模板身份标记格式无效：{name}")
        else:
            values[name] = parsed

    if issues:
        return None, "declared", tuple(issues)
    template_id = values[markers["template_id"]]
    template_version = values[markers["template_version"]]
    revision = values[markers["template_contract_revision"]]
    entry = next((item for item in TEMPLATE_MANIFEST["templates"]
                  if item.get("template_id") == template_id
                  and item.get("template_version") == template_version
                  and item.get("input_compatibility") == "ACCEPTED"), None)
    if entry is None:
        return None, "declared", (
            f"不支持的模板身份：{template_id} / {template_version}",)
    if revision != str(entry.get("template_contract_revision") or ""):
        issues.append(
            f"模板契约修订不匹配：声明 {revision}，清单期望 "
            f"{entry.get('template_contract_revision', '')}")

    expected_sheets = {sheet["sheet_id"]: str(sheet.get("contract_revision") or "")
                       for sheet in entry.get("sheets", ())}
    for sheet_id, expected_revision in expected_sheets.items():
        name = f"{markers['sheet_contract_prefix']}{sheet_id}"
        items = names.get(name, ())
        if len(items) != 1:
            issues.append(f"Sheet 契约标记缺失或重复：{sheet_id}")
            continue
        actual_revision = _string_name_value(items[0])
        if actual_revision != expected_revision:
            if (sheet_id == "motor" and actual_revision == "motor-input.v1"
                    and expected_revision == "motor-input.v2"):
                issues.append(
                    "电动机候选模板已更新，请重新输出空白模板并复制输入数据；旧文件不会被修改。")
            issues.append(
                f"Sheet 契约修订不匹配：{sheet_id} 声明 {actual_revision!r}，"
                f"清单期望 {expected_revision!r}")
    unexpected_sheet_markers = sorted(
        name[len(markers["sheet_contract_prefix"]):]
        for name in prefixed_markers
        if name[len(markers["sheet_contract_prefix"]):] not in expected_sheets)
    if unexpected_sheet_markers:
        issues.append("存在未登记的 Sheet 契约标记：" + "、".join(unexpected_sheet_markers))
    return entry, "declared", tuple(issues)


class V6TemplateResource:
    """正式 V6 统一模板资源（Windows V1 的正式用户模板）。"""

    def __init__(self, resource_dir: Path | None = None,
                 *, template_name: str = DEFAULT_V6_TEMPLATE):
        self._temporary_resource_dir: tempfile.TemporaryDirectory[str] | None = None
        if resource_dir is not None:
            self.resource_dir = Path(resource_dir)
            self.template_path = self.resource_dir / template_name
            return

        filesystem_dir = Path(__file__).resolve().parents[2] / "resources" / "templates"
        filesystem_path = filesystem_dir / template_name
        if filesystem_path.is_file():
            self.resource_dir = filesystem_dir
            self.template_path = filesystem_path
            return

        try:
            bundled = resources.files("equipeffi").joinpath(
                "resources", "templates", template_name)
            if bundled.is_file():
                self._temporary_resource_dir = tempfile.TemporaryDirectory(
                    prefix="equipeffi-template-")
                self.resource_dir = Path(self._temporary_resource_dir.name)
                self.template_path = self.resource_dir / template_name
                self.template_path.write_bytes(bundled.read_bytes())
                return
        except (FileNotFoundError, ModuleNotFoundError, OSError):
            pass
        self.resource_dir = filesystem_dir
        self.template_path = filesystem_path

    def fingerprint(self) -> str:
        if not self.template_path.is_file():
            raise TemplateResourceError(f"内置V6模板不存在：{self.template_path}")
        digest = sha256()
        with self.template_path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @property
    def identity(self) -> dict[str, str]:
        return dict(V6_TEMPLATE_IDENTITY)

    def validate(self, path: Path | None = None, *,
                 check_pump_sheet: bool = True) -> TemplateValidationResult:
        candidate = path or self.template_path
        sheet_names = _workbook_sheet_names(candidate)
        entry, identity_source, identity_issues = _resolve_v6_identity(candidate)
        contract_entry = entry or V6_TEMPLATE_ENTRY
        expected_sheets = tuple(
            sheet["sheet_name"] for sheet in contract_entry.get("sheets", ())
        ) or REQUIRED_V6_SHEETS
        missing = tuple(sheet for sheet in expected_sheets if sheet not in sheet_names)
        issues = list(identity_issues)
        if sheet_names != expected_sheets:
            issues.append(
                "Sheet 集合或顺序与模板契约不符："
                f"实际 {sheet_names!r}，期望 {expected_sheets!r}")

        pump_contract = next((sheet for sheet in contract_entry.get("sheets", ())
                              if sheet.get("sheet_id") == "centrifugal_pump"), None)
        if pump_contract is None:
            issues.append("模板清单没有离心泵 Sheet 契约")
        elif check_pump_sheet and pump_contract["sheet_name"] in sheet_names:
            try:
                with OOXMLWorkbook(candidate) as workbook:
                    grid = workbook.rows(pump_contract["sheet_name"])
                    merged_ranges = workbook.merged_ranges(
                        pump_contract["sheet_name"])
                issues.extend(pump_data_layout_issues(
                    merged_ranges, pump_contract))
                header_index = int(pump_contract["header_row"]) - 1
                if header_index < 0 or header_index >= len(grid):
                    issues.append(f"离心泵表头行无效：{pump_contract['header_row']}")
                else:
                    issues.extend(pump_header_issues(grid[header_index], pump_contract))
            except (OOXMLReadError, KeyError, TypeError, ValueError) as exc:
                issues.append(f"无法验证离心泵 Sheet 契约：{exc}")

        digest = sha256(candidate.read_bytes()).hexdigest()
        valid = entry is not None and not missing and not issues
        if valid:
            message = "V6模板结构检查通过"
        else:
            details = list(issues)
            if missing:
                details.append("缺少工作表：" + "、".join(missing))
            message = "V6模板不兼容：" + "；".join(details or ["未知模板版本"])
        identity = _entry_identity(entry) if entry is not None else {}
        sheet_contracts = ({
            str(sheet["sheet_id"]): str(sheet.get("contract_revision") or "")
            for sheet in contract_entry.get("sheets", ())
        } if entry is not None else {})
        return TemplateValidationResult(
            str(candidate), digest, sheet_names, missing, valid, message,
            identity=identity, sheet_contracts=sheet_contracts,
            identity_source=identity_source, pump_sheet_contract=pump_contract,
            issues=tuple(issues))

    def download_to(self, destination: Path) -> Path:
        source = self.template_path.resolve()
        target = destination.resolve()
        if source == target:
            raise TemplateResourceError("下载目标不能覆盖内置V6模板")
        if not source.is_file():
            raise TemplateResourceError(f"内置V6模板不存在：{source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target


class V61TransformerTemplateResource(V6TemplateResource):
    """显式提供 V6.1 候选模板；不改变 V6 资源的默认选择。"""

    def __init__(self, resource_dir: Path | None = None,
                 *, template_name: str = DEFAULT_V61_TEMPLATE):
        super().__init__(resource_dir, template_name=template_name)

    @property
    def identity(self) -> dict[str, str]:
        return dict(V61_TEMPLATE_IDENTITY)

    def validate(self, path: Path | None = None, *,
                 check_pump_sheet: bool = True) -> TemplateValidationResult:
        base = super().validate(path, check_pump_sheet=check_pump_sheet)
        # A caller may use this resource to validate an older source workbook.
        # Its transformer Sheet remains explicitly unprocessed.
        if not base.is_valid:
            return base
        if base.identity.get("template_version") != "V6.1":
            return _version_mismatch(base, "V6.1")

        contract = TRANSFORMER_SHEET_CONTRACT
        candidate = Path(path) if path is not None else self.template_path
        issues = list(base.issues)
        try:
            with OOXMLWorkbook(candidate) as workbook:
                grid = workbook.rows(str(contract["sheet_name"]))
                merged_ranges = workbook.merged_ranges(str(contract["sheet_name"]))
            issues.extend(sheet_data_layout_issues(merged_ranges, contract))
            header_row = int(contract["header_row"]) - 1
            if header_row < 0 or header_row >= len(grid):
                issues.append("「变压器」Sheet 缺少正式表头行")
            else:
                header = grid[header_row]
                for field in contract["fields"]:
                    column = str(field["column"])
                    index = _column_index(column)
                    value = header[index] if index < len(header) else ""
                    label, unit, extra = _header_parts(value)
                    expected_label = str(field.get("label") or "")
                    expected_unit = str(field.get("unit") or "")
                    if (label != expected_label or unit != expected_unit or extra):
                        expected = expected_label + (
                            f" ({expected_unit})" if expected_unit else "")
                        actual = label + (f" ({unit})" if unit else "")
                        issues.append(
                            f"变压器 {column} 列期望「{expected}」，实际为「{actual}」")
        except (OOXMLReadError, KeyError, TypeError, ValueError) as exc:
            issues.append(f"无法验证变压器 Sheet 契约：{exc}")

        is_valid = not issues and not base.missing_sheets
        message = ("V6.1模板结构检查通过" if is_valid else
                   "V6.1模板不兼容：" + "；".join(issues or ["模板结构无效"]))
        return TemplateValidationResult(
            path=base.path, sha256=base.sha256, sheet_names=base.sheet_names,
            missing_sheets=base.missing_sheets, is_valid=is_valid,
            message=message, identity=base.identity,
            sheet_contracts=base.sheet_contracts,
            identity_source=base.identity_source,
            pump_sheet_contract=base.pump_sheet_contract,
            issues=tuple(issues))


class V62MotorTemplateResource(V6TemplateResource):
    """Candidate V6.2 template with a mechanically verified motor contract."""

    def __init__(self, resource_dir: Path | None = None,
                 *, template_name: str = DEFAULT_V62_TEMPLATE):
        super().__init__(resource_dir, template_name=template_name)

    @property
    def identity(self) -> dict[str, str]:
        return dict(V62_TEMPLATE_IDENTITY)

    def validate(self, path: Path | None = None, *,
                 check_pump_sheet: bool = True) -> TemplateValidationResult:
        base = super().validate(path, check_pump_sheet=check_pump_sheet)
        if not base.is_valid:
            return base
        if base.identity.get("template_version") != "V6.2":
            return _version_mismatch(base, "V6.2")

        candidate = Path(path) if path is not None else self.template_path
        issues = list(base.issues)
        transformer_contract = next(
            (sheet for sheet in V62_TEMPLATE_ENTRY["sheets"]
             if sheet.get("sheet_id") == "transformer"), None)
        if transformer_contract is None:
            issues.append("V6.2清单缺少变压器Sheet契约")
        else:
            issues.extend(_transformer_sheet_issues(candidate, transformer_contract))

        motor_contract = MOTOR_SHEET_CONTRACT
        issues.extend(_motor_manifest_contract_issues(motor_contract))
        try:
            with OOXMLWorkbook(candidate) as workbook:
                grid = workbook.rows(str(motor_contract["sheet_name"]))
                merged_ranges = workbook.merged_ranges(str(motor_contract["sheet_name"]))
                motor_part = workbook._sheets[str(motor_contract["sheet_name"])]
                motor_xml = workbook.archive.read(motor_part)
                notes_contract = next(
                    sheet for sheet in V62_TEMPLATE_ENTRY["sheets"]
                    if sheet.get("sheet_id") == "template_notes")
                notes = workbook.rows(str(notes_contract["sheet_name"]))
                instructions_contract = next(
                    sheet for sheet in V62_TEMPLATE_ENTRY["sheets"]
                    if sheet.get("sheet_id") == "instructions")
                instructions = workbook.rows(str(instructions_contract["sheet_name"]))
                configuration_contract = next(
                    sheet for sheet in V62_TEMPLATE_ENTRY["sheets"]
                    if sheet.get("sheet_id") == "configuration")
                configuration_name = str(configuration_contract["sheet_name"])
                config_rows = workbook.rows(configuration_name)
                config_part = workbook._sheets[configuration_name]
            issues.extend(sheet_data_layout_issues(merged_ranges, motor_contract))
            header_index = int(motor_contract["header_row"]) - 1
            if header_index < 0 or header_index >= len(grid):
                issues.append("「电动机」Sheet缺少正式表头行")
            else:
                for field in motor_contract["fields"]:
                    column = str(field["column"])
                    index = _column_index(column)
                    value = grid[header_index][index] if index < len(grid[header_index]) else ""
                    label, unit, extra = _header_parts(value)
                    expected_label = str(field.get("label") or "")
                    expected_unit = str(field.get("unit") or "")
                    if label != expected_label or unit != expected_unit or extra:
                        expected = expected_label + (f" ({expected_unit})" if expected_unit else "")
                        actual = label + (f" ({unit})" if unit else "")
                        issues.append(f"电动机 {column} 列期望「{expected}」，实际为「{actual}」")

            motor_root = ElementTree.fromstring(motor_xml)
            namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            formulas_in_t = [
                cell.attrib.get("r", "")
                for cell in motor_root.findall(
                    f"{{{namespace}}}sheetData/{{{namespace}}}row/{{{namespace}}}c")
                if re.fullmatch(r"T(?:[4-9]|[1-9][0-9]+)", cell.attrib.get("r", ""))
                and cell.find(f"{{{namespace}}}f") is not None
            ]
            if formulas_in_t:
                issues.append("电动机T列仍含有已退役自动业务公式")

            expected_validation_columns = {"D", "F", "G", "H", "I", "J", "K", "L", "M"}
            validations = motor_root.findall(
                f"{{{namespace}}}dataValidations/{{{namespace}}}dataValidation")
            by_column: dict[str, list[ElementTree.Element]] = {}
            for validation in validations:
                reference = str(validation.attrib.get("sqref", ""))
                match = re.fullmatch(r"([A-Z]+)4:\1(?:[1-9][0-9]*)", reference)
                if match:
                    by_column.setdefault(match.group(1), []).append(validation)
            if set(by_column) != expected_validation_columns or any(
                    len(nodes) != 1 for nodes in by_column.values()):
                issues.append("电动机D:M输入校验范围与九列输入契约不一致")
            else:
                def validation_for(column: str) -> ElementTree.Element | None:
                    return by_column[column][0] if len(by_column.get(column, ())) == 1 else None

                def formula_for(node: ElementTree.Element | None, child: str) -> str:
                    if node is None:
                        return ""
                    found = node.find(f"{{{namespace}}}{child}")
                    return (found.text or "") if found is not None else ""

                requirements = {
                    "D": ("whole", "greaterThan", "0", ""),
                    "F": ("list", "", "EV_MOTOR_V62_CATEGORY", ""),
                    "I": ("list", "", "EV_MOTOR_V62_BASIS", ""),
                    "M": ("decimal", "between", "1", "100"),
                }
                for column, (kind, operator, first, second) in requirements.items():
                    node = validation_for(column)
                    actual = (
                        node.attrib.get("type", "") if node is not None else "",
                        node.attrib.get("operator", "") if node is not None else "",
                        formula_for(node, "formula1"), formula_for(node, "formula2"))
                    if actual != (kind, operator, first, second):
                        issues.append(f"电动机{column}列数据验证与输入契约不一致")
                for column in ("G", "J", "L"):
                    node = validation_for(column)
                    if (node is None or node.attrib.get("type") != "decimal"
                            or node.attrib.get("operator") not in {"greaterThan", "greaterThanOrEqual"}
                            or formula_for(node, "formula1") not in {"0", "0.0"}):
                        issues.append(f"电动机{column}列数据验证不是非负数值输入")
                motor_fields = {
                    str(field.get("field_id")): field
                    for field in motor_contract.get("fields", ())
                    if field.get("field_id")
                }
                for field_id in ("rated_frequency_hz", "poles"):
                    field = motor_fields.get(field_id, {})
                    rule = field.get("excel_validation") or {}
                    column = str(rule.get("column") or field.get("column") or "")
                    node = validation_for(column) if column else None
                    actual = {
                        "type": node.attrib.get("type", "") if node is not None else "",
                        "formula1": formula_for(node, "formula1"),
                        "error_title": node.attrib.get("errorTitle", "") if node is not None else "",
                        "error": node.attrib.get("error", "") if node is not None else "",
                        "prompt_title": node.attrib.get("promptTitle", "") if node is not None else "",
                        "prompt": node.attrib.get("prompt", "") if node is not None else "",
                    }
                    expected = {
                        key: rule.get(key)
                        for key in ("type", "formula1", "error_title", "error",
                                    "prompt_title", "prompt")
                    }
                    if actual != expected:
                        issues.append(f"电动机{column}列数据验证与输入契约不一致")

            fixed_labels = (
                "本次批量处理说明", "模板版本", "处理时间", "已评价Sheet",
                "未评价Sheet", "统计口径", "未评价提示", "软件区域标识",
            )
            for offset, expected_label in enumerate(fixed_labels, start=27):
                row_index = offset - 1
                actual = notes[row_index][0] if row_index < len(notes) and notes[row_index] else ""
                if actual != expected_label:
                    issues.append(f"模板说明!A{offset}固定批次说明标签不一致")
            template_detail = (
                notes[20][1]
                if len(notes) > 20 and len(notes[20]) > 1 else "")
            instruction_summary = (
                instructions[13][7]
                if len(instructions) > 13 and len(instructions[13]) > 7 else "")
            for category in MOTOR_CATEGORIES:
                if category.table_no is None:
                    continue
                scope = motor_scope_hint(category.category_id)
                basis = motor_efficiency_basis_hint(category.category_id)
                if scope and scope not in str(template_detail):
                    issues.append(
                        f"模板说明!B21缺少{category.label}适用范围提示")
                if basis and basis not in str(template_detail):
                    issues.append(
                        f"模板说明!B21缺少{category.label}试验口径提示")
                if ((scope and scope not in str(instruction_summary))
                        or (basis and basis not in str(instruction_summary))):
                    issues.append(
                        f"注意事项!H14缺少{category.label}完整说明")
            stale_motor_guidance = (
                "三类标准合并到一张表", "额定电压统一为kV文本档",
                "变频调速永磁同步电动机按90%额定转速",
            )
            if any(text in str(template_detail) for text in stale_motor_guidance):
                issues.append("模板说明!B21仍保留已退役的电动机输入说明")
            # Column G in the hidden config region holds no motor contract. Keep a
            # local reference here to force a parse of the complete config part.
            if not config_rows:
                issues.append("配置Sheet为空，无法验证电动机模板契约")
            if not config_part:
                issues.append("配置Sheet部件缺失")
            issues.extend(_motor_config_issues(candidate, V62_TEMPLATE_ENTRY))
        except (OOXMLReadError, KeyError, TypeError, ValueError,
                ElementTree.ParseError) as exc:
            issues.append(f"无法验证电动机Sheet契约：{exc}")

        is_valid = not issues and not base.missing_sheets
        message = ("V6.2模板结构检查通过" if is_valid else
                   "V6.2模板不兼容：" + "；".join(issues or ["模板结构无效"]))
        return TemplateValidationResult(
            path=base.path, sha256=base.sha256, sheet_names=base.sheet_names,
            missing_sheets=base.missing_sheets, is_valid=is_valid,
            message=message, identity=base.identity,
            sheet_contracts=base.sheet_contracts,
            identity_source=base.identity_source,
            pump_sheet_contract=base.pump_sheet_contract,
            issues=tuple(issues))


def validate_v6_template(path: Path, *, check_pump_sheet: bool = True
                         ) -> TemplateValidationResult:
    """Validate any accepted unified V6 generation with its own Sheet contracts."""
    base = V6TemplateResource().validate(path, check_pump_sheet=check_pump_sheet)
    version = (base.identity or {}).get("template_version")
    if version == "V6.1":
        return V61TransformerTemplateResource().validate(
            path, check_pump_sheet=check_pump_sheet)
    if version == "V6.2":
        return V62MotorTemplateResource().validate(
            path, check_pump_sheet=check_pump_sheet)
    return base
