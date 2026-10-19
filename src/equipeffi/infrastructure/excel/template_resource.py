from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib.resources as resources
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from .ooxml_reader import OOXMLReadError, OOXMLWorkbook


DEFAULT_V4_TEMPLATE = "设备能效分析空白模板_重构版V4_20260825.xlsx"

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
V6_TEMPLATE_ENTRY: dict[str, Any] = next(
    entry for entry in TEMPLATE_MANIFEST["templates"]
    if entry.get("template_id") == TEMPLATE_MANIFEST["formal_windows_v1_template"]
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
REQUIRED_V4_SHEETS: tuple[str, ...] = (
    "注意事项",
    "模板说明",
    "配置",
    "变压器",
    "电动机",
    "空压机",
    "离心泵",
    "离心通风机",
    "轴流通风机",
    "鼓风机",
    "潜水电泵",
    "工业锅炉",
    "热处理设备",
    "热泵和冷水机组",
    "热泵热水机",
    "风管送风式空调",
    "单元式空调",
    "多联式空调",
)


class TemplateResourceError(ValueError):
    """模板资源不存在、损坏或结构不符合V4契约。"""


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


class V4TemplateResource:
    """内置V4空白模板资源管理器。

    只复制模板，不在源文件上写入；Excel读取/回写由后续适配器负责。
    """

    def __init__(self, resource_dir: Path | None = None, *, template_name: str = DEFAULT_V4_TEMPLATE):
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

        # A wheel can be imported directly from a zip path (and some mobile
        # bridges use the same resource loader).  ``Path(__file__)`` is then
        # not a real filesystem path, so materialize only this small template
        # into a managed temporary directory.
        try:
            bundled = resources.files("equipeffi").joinpath("resources", "templates", template_name)
            if bundled.is_file():
                self._temporary_resource_dir = tempfile.TemporaryDirectory(prefix="equipeffi-template-")
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
            raise TemplateResourceError(f"内置V4模板不存在：{self.template_path}")
        digest = sha256()
        with self.template_path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def validate(self, path: Path | None = None) -> TemplateValidationResult:
        candidate = path or self.template_path
        sheet_names = _workbook_sheet_names(candidate)
        missing = tuple(sheet for sheet in REQUIRED_V4_SHEETS if sheet not in sheet_names)
        digest = sha256(candidate.read_bytes()).hexdigest()
        valid = not missing
        message = "V4模板结构检查通过" if valid else f"缺少V4工作表：{'、'.join(missing)}"
        return TemplateValidationResult(str(candidate), digest, sheet_names, missing, valid, message)

    def download_to(self, destination: Path) -> Path:
        source = self.template_path.resolve()
        target = destination.resolve()
        if source == target:
            raise TemplateResourceError("下载目标不能覆盖内置V4模板")
        if not source.is_file():
            raise TemplateResourceError(f"内置V4模板不存在：{source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target


class V6TemplateResource(V4TemplateResource):
    """正式 V6 统一模板资源（Phase 8 起 Windows V1 的正式用户模板）。

    复用 V4 的资源定位与"只复制、不写源文件"语义，只替换模板身份与结构契约。
    """

    def __init__(self, resource_dir: Path | None = None,
                 *, template_name: str = DEFAULT_V6_TEMPLATE):
        super().__init__(resource_dir, template_name=template_name)

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
