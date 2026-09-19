from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from .template_resource import REQUIRED_V4_SHEETS, V4TemplateResource


_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS = {"main": _MAIN_NS}
_FORBIDDEN_TOKENS = ("设备位号", "是否在标准适用范围")
_FORMULA_ERRORS = ("#REF!", "#VALUE!", "#NAME?", "#DIV/0!", "#N/A", "#NUM!", "#NULL!")
_EXPECTED_CURRENT_STANDARDS = frozenset({
    "GB 20052-2024", "GB 18613-2020", "GB 30254-2024", "GB 30253-2024",
    "GB 19153-2019", "GB 19762-2025", "GB 19761-2020", "GB 28381-2012",
    "GB 32030-2022", "GB 24500-2020", "GB/T 36561-2018", "GB 19577-2024",
    "GB 29541-2013", "GB 37479-2019", "GB 19576-2019", "GB 21454-2021",
})


@dataclass(frozen=True)
class V4TemplateAuditResult:
    path: str
    is_valid: bool
    sheet_names: tuple[str, ...]
    missing_sheets: tuple[str, ...]
    unprotected_sheets: tuple[str, ...]
    forbidden_fields: tuple[str, ...]
    formula_errors: tuple[str, ...]
    volatile_formulas: tuple[str, ...]
    formula_count: int
    media_parts: tuple[str, ...]
    workbook_protected: bool
    calc_on_load: bool
    standard_catalog_count: int
    standard_catalog_codes: tuple[str, ...]
    future_standard_status: str
    standard_catalog_issues: tuple[str, ...]
    warnings: tuple[str, ...]


def _inline_cell_text(sheet_xml: bytes, column: str, row_number: int) -> str:
    """Read a small inline-string cell without requiring openpyxl."""

    try:
        root = ElementTree.fromstring(sheet_xml)
    except ElementTree.ParseError:
        return ""
    cell = root.find(f".//main:c[@r='{column}{row_number}']", _NS)
    if cell is None:
        return ""
    return "".join(node.text or "" for node in cell.findall(".//main:t", _NS)).strip()


def _standard_catalog_audit(sheet_xml: bytes) -> tuple[int, tuple[str, ...], str, tuple[str, ...]]:
    """Validate the 16 current standards and the future blower entry.

    The V4 workbook stores the catalog as inline strings, so this check stays
    independent of optional spreadsheet libraries and also works in a wheel
    installed on Linux/Android bridges.
    """

    if not sheet_xml:
        return 0, (), "", ("缺少注意事项sheet",)
    try:
        root = ElementTree.fromstring(sheet_xml)
    except ElementTree.ParseError:
        return 0, (), "", ("注意事项sheet XML无效",)
    current_codes: list[str] = []
    future_status = ""
    for row in root.findall(".//main:sheetData/main:row", _NS):
        values: dict[str, str] = {}
        for cell in row.findall("main:c", _NS):
            ref = cell.attrib.get("r", "")
            column = re.sub(r"\d+", "", ref)
            values[column] = "".join(node.text or "" for node in cell.findall(".//main:t", _NS)).strip()
        code = values.get("B", "")
        status = values.get("G", "")
        if re.fullmatch(r"GB(?:/T)?\s*\d{4,5}-\d{4}", code):
            if code == "GB 28381-2026":
                future_status = status
            elif "现行" in status:
                current_codes.append(code)
    expected = 16
    issues: list[str] = []
    if len(current_codes) != expected:
        issues.append(f"注意事项现行标准数量应为{expected}项，实际{len(current_codes)}项")
    current_set = set(current_codes)
    missing_codes = sorted(_EXPECTED_CURRENT_STANDARDS - current_set)
    unexpected_codes = sorted(current_set - _EXPECTED_CURRENT_STANDARDS)
    if missing_codes:
        issues.append("注意事项缺少现行标准：" + "、".join(missing_codes))
    if unexpected_codes:
        issues.append("注意事项包含未列入本模板的现行标准：" + "、".join(unexpected_codes))
    if future_status != "已发布、未实施":
        issues.append("注意事项未正确标注GB 28381-2026为“已发布、未实施”")
    return len(current_codes), tuple(current_codes), future_status, tuple(issues)


def audit_v4_template(path: Path) -> V4TemplateAuditResult:
    """检查V4模板的结构、保护、公式和禁止字段，不修改输入文件。"""
    candidate = Path(path)
    try:
        with ZipFile(candidate) as archive:
            names = tuple(archive.namelist())
            workbook_xml = archive.read("xl/workbook.xml")
            sheet_xml: dict[str, bytes] = {}
            workbook_root = ElementTree.fromstring(workbook_xml)
            rel_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relations = {
                node.attrib.get("Id", ""): node.attrib.get("Target", "")
                for node in rel_root
            }
            for node in workbook_root.findall("main:sheets/main:sheet", _NS):
                sheet_name = node.attrib.get("name", "")
                target = relations.get(node.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", ""), "")
                if target.startswith("/"):
                    target = target.lstrip("/")
                elif target and not target.startswith("xl/"):
                    target = "xl/" + target
                if sheet_name and target in names:
                    sheet_xml[sheet_name] = archive.read(target)
    except (OSError, BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise ValueError(f"无法审计V4模板：{exc}") from exc

    sheet_names = tuple(sheet_xml)
    missing = tuple(name for name in REQUIRED_V4_SHEETS if name not in sheet_names)
    equipment_sheets = tuple(name for name in REQUIRED_V4_SHEETS if name not in {"注意事项", "模板说明", "配置"})
    unprotected = tuple(
        name for name in equipment_sheets
        if b"<sheetProtection" not in sheet_xml.get(name, b"")
    )
    full_text = b"\n".join((workbook_xml, *sheet_xml.values())).decode("utf-8", errors="ignore")
    # “注意事项”允许说明已删除的旧字段；只有出现在表头/配置字段中的同名项才算违规。
    forbidden = tuple(
        token for token in _FORBIDDEN_TOKENS
        if token in full_text and f"不设置“{token}”列" not in full_text
    )
    formula_count = full_text.count("<f")
    formula_errors = tuple(token for token in _FORMULA_ERRORS if token in full_text)
    volatile_formulas = tuple(
        token for token in ("INDIRECT(", "OFFSET(") if token in full_text.upper()
    )
    workbook_protected = b"<workbookProtection" in workbook_xml
    calc_on_load = b"fullCalcOnLoad=\"1\"" in workbook_xml and b"forceFullCalc=\"1\"" in workbook_xml
    standard_count, standard_codes, future_status, catalog_issues = _standard_catalog_audit(sheet_xml.get("注意事项", b""))
    # OOXML中selectUnlockedCells="0"表示不禁止选择未锁定单元格；模板同时
    # 使用selectLockedCells="1"，符合“可编辑单元格可选、锁定单元格不可选”的约定。
    warnings: list[str] = []

    return V4TemplateAuditResult(
        path=str(candidate),
        is_valid=not (
            missing or unprotected or forbidden or formula_errors or volatile_formulas
            or not workbook_protected or catalog_issues
        ),
        sheet_names=sheet_names,
        missing_sheets=missing,
        unprotected_sheets=unprotected,
        forbidden_fields=forbidden,
        formula_errors=formula_errors,
        volatile_formulas=volatile_formulas,
        formula_count=formula_count,
        media_parts=tuple(name for name in names if name.startswith("xl/media/")),
        workbook_protected=workbook_protected,
        calc_on_load=calc_on_load,
        standard_catalog_count=standard_count,
        standard_catalog_codes=standard_codes,
        future_standard_status=future_status,
        standard_catalog_issues=catalog_issues,
        warnings=tuple(warnings),
    )


class V4TemplateAudit:
    """面向桌面、服务端和移动端适配器的只读模板审计入口。"""

    def audit(self, path: Path) -> V4TemplateAuditResult:
        return audit_v4_template(path)


__all__ = ["V4TemplateAudit", "V4TemplateAuditResult", "audit_v4_template"]
