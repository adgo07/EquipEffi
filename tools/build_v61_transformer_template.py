"""从已资产化的V6模板派生V6.1，不重存或改写离心泵工作表。

变压器字段、类别与标准条件选项来自 Domain input contract。生成过程只改变压器
Sheet、配置Sheet中专属的变压器选项区域、变压器表定义和新模板身份；其余OOXML
部件按原始字节复制。
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import posixpath
from pathlib import Path
import re
import sys
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from equipeffi.domain.devices.transformer.input_contract import (  # noqa: E402
    TRANSFORMER_CATEGORIES,
    TRANSFORMER_SCOPE_HINT,
    condition_options,
)
from equipeffi.infrastructure.excel.template_resource import (  # noqa: E402
    DEFAULT_V61_TEMPLATE,
    TEMPLATE_MANIFEST,
    V6_TEMPLATE_IDENTITY,
    V61_TEMPLATE_ENTRY,
    identity_defined_names,
)

DEFAULT_SOURCE = ROOT / "src" / "equipeffi" / "resources" / "templates" / V6_TEMPLATE_IDENTITY["filename"]
DEFAULT_OUTPUT = ROOT / "src" / "equipeffi" / "resources" / "templates" / DEFAULT_V61_TEMPLATE
MANIFEST_PATH = ROOT / "src" / "equipeffi" / "resources" / "TEMPLATE_MANIFEST.json"

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("", MAIN_NS)
ET.register_namespace("r", REL_NS)

TRANSFORMER_SHEET = "变压器"
CONFIG_SHEET = "配置"
FIRST_DATA_ROW = 4
LAST_DATA_ROW = 103
HEADER_ROW = 3
TRANSFORMER_CONDITION_FIRST_COLUMN = 116  # DL; DK holds category IDs.
LEGACY_CONDITION_COLUMNS = range(104, 115)  # CZ:DJ, no longer referenced.

HEADERS = {
    "I": "额定阻抗\n(%)",
    "J": "空载损耗\n(W)",
    "K": "负载损耗\n(W)",
    "R": "能效结论",
    "U": "自动备注",
    "V": "高压额定电压\n(kV)",
    "W": "低压额定电压\n(kV)",
    "X": "额定阻抗高—低\n(%)",
    "Y": "额定阻抗中—低\n(%)",
}


def _tag(local: str) -> str:
    return f"{{{MAIN_NS}}}{local}"


def _column_number(letters: str) -> int:
    result = 0
    for char in letters.upper():
        result = result * 26 + ord(char) - ord("A") + 1
    return result


def _column_letters(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _option_label(option: Any) -> str:
    value = _field(option, "label")
    if value is None:
        value = _field(option, "visible_name")
    if value is None and isinstance(option, str):
        value = option
    if value is None:
        raise ValueError(f"输入契约选项缺少label：{option!r}")
    return str(value)


def _category_id(option: Any) -> str:
    value = _field(option, "category_id")
    if value is None:
        raise ValueError(f"变压器类别缺少稳定ID：{option!r}")
    return str(value)


def _condition_options(category_id: str) -> tuple[Any, ...]:
    return tuple(condition_options(category_id))


def _read_namespaces(xml: bytes) -> None:
    import io

    for _event, pair in ET.iterparse(io.BytesIO(xml), events=("start-ns",)):
        prefix, uri = pair
        ET.register_namespace(prefix or "", uri)


def _parse_xml(xml: bytes) -> ET.Element:
    _read_namespaces(xml)
    return ET.fromstring(xml)


def _xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _relationship_target(package: ZipFile, owner_path: str, rel_id: str) -> str:
    owner_dir = owner_path.rsplit("/", 1)[0]
    rel_path = f"{owner_dir}/_rels/{owner_path.rsplit('/', 1)[1]}.rels"
    root = _parse_xml(package.read(rel_path))
    for node in root.findall(f"{{{PKG_REL_NS}}}Relationship"):
        if node.attrib.get("Id") != rel_id:
            continue
        target = node.attrib.get("Target", "")
        if target.startswith("/"):
            return target.lstrip("/")
        return str(Path(owner_dir, target)).replace("\\", "/")
    raise ValueError(f"找不到OOXML关系：{owner_path} / {rel_id}")


def _sheet_target(package: ZipFile, sheet_name: str) -> str:
    workbook = _parse_xml(package.read("xl/workbook.xml"))
    rel_root = _parse_xml(package.read("xl/_rels/workbook.xml.rels"))
    relations = {node.attrib.get("Id", ""): node.attrib.get("Target", "")
                 for node in rel_root.findall(f"{{{PKG_REL_NS}}}Relationship")}
    for sheet in workbook.findall(f"{_tag('sheets')}/{_tag('sheet')}"):
        if sheet.attrib.get("name") != sheet_name:
            continue
        rel_id = sheet.attrib.get(f"{{{REL_NS}}}id", "")
        target = relations.get(rel_id, "")
        if not target:
            break
        if target.startswith("/"):
            return target.lstrip("/")
        return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError(f"模板缺少工作表：{sheet_name}")


def _sheet_table_target(package: ZipFile, sheet_path: str, table_name: str) -> str:
    rel_path = f"{sheet_path.rsplit('/', 1)[0]}/_rels/{sheet_path.rsplit('/', 1)[1]}.rels"
    root = _parse_xml(package.read(rel_path))
    for node in root.findall(f"{{{PKG_REL_NS}}}Relationship"):
        if not node.attrib.get("Type", "").endswith("/table"):
            continue
        target = node.attrib.get("Target", "")
        if target.startswith("/"):
            path = target.lstrip("/")
        else:
            path = posixpath.normpath(
                posixpath.join(sheet_path.rsplit("/", 1)[0], target))
        data = package.read(path)
        table = _parse_xml(data)
        if table.attrib.get("name") == table_name:
            return path
    raise ValueError(f"找不到表定义：{table_name}")


def _cell_map(row: ET.Element) -> dict[str, ET.Element]:
    result = {}
    for cell in row.findall(_tag("c")):
        match = re.match(r"([A-Z]+)", cell.attrib.get("r", ""))
        if match:
            result[match.group(1)] = cell
    return result


def _set_inline(cell: ET.Element, value: str) -> None:
    for child in list(cell):
        cell.remove(child)
    cell.attrib["t"] = "inlineStr"
    inline = ET.SubElement(cell, _tag("is"))
    text = ET.SubElement(inline, _tag("t"))
    if value != value.strip():
        text.attrib[f"{{{XML_NS}}}space"] = "preserve"
    text.text = value


def _blank_cell(reference: str, style: str | None) -> ET.Element:
    attrs = {"r": reference, "t": "n"}
    if style:
        attrs["s"] = style
    return ET.Element(_tag("c"), attrs)


def _formula_cell(reference: str, style: str | None, formula: str) -> ET.Element:
    cell = _blank_cell(reference, style)
    cell.attrib.pop("t", None)
    ET.SubElement(cell, _tag("f")).text = formula
    ET.SubElement(cell, _tag("v"))
    return cell


def _row_from_template(template: ET.Element, number: int,
                       cell_styles: dict[str, str | None]) -> ET.Element:
    row = ET.Element(template.tag, dict(template.attrib))
    row.attrib["r"] = str(number)
    row.attrib["spans"] = "1:25"
    formula = f'IF(COUNTA(B{number}:K{number},S{number}:T{number},V{number}:Y{number})>0,ROW()-3,"")'
    cells = [_formula_cell(f"A{number}", cell_styles.get("A"), formula)]
    cells.extend(_blank_cell(f"{column}{number}", cell_styles.get(column))
                 for column in list("BCDEFGHIJKLMNOPQRSTUVWXYZ")
                 if column in cell_styles and column != "A")
    for cell in cells:
        row.append(cell)
    return row


def _patch_transformer_sheet(xml: bytes, loss_style: str) -> bytes:
    root = _parse_xml(xml)
    dimension = root.find(_tag("dimension"))
    if dimension is not None:
        dimension.attrib["ref"] = "A1:Y103"
    cols = root.find(_tag("cols"))
    if cols is not None:
        old_v = next((node for node in cols.findall(_tag("col"))
                      if node.attrib.get("min") == "22" and node.attrib.get("max") == "22"), None)
        if old_v is not None:
            old_v.attrib["min"] = "22"
            old_v.attrib["max"] = "25"
            old_v.attrib["width"] = "16"
            old_v.attrib["customWidth"] = "1"
            old_v.attrib.pop("hidden", None)
        else:
            ET.SubElement(cols, _tag("col"), {
                "min": "22", "max": "25", "width": "16", "customWidth": "1"})

    sheet_data = root.find(_tag("sheetData"))
    if sheet_data is None:
        raise ValueError("变压器Sheet缺少sheetData")
    rows = {int(row.attrib["r"]): row for row in sheet_data.findall(_tag("row"))
            if row.attrib.get("r", "").isdigit()}
    header = rows.get(HEADER_ROW)
    if header is None:
        raise ValueError("变压器Sheet缺少第3行表头")
    header_cells = _cell_map(header)
    header_style = header_cells.get("I", header_cells.get("U"))
    result_header_style = header_cells.get("U", header_style)
    for column, label in HEADERS.items():
        cell = header_cells.get(column)
        if cell is None:
            source = result_header_style if column in {"U"} else header_style
            attrs = {"r": f"{column}{HEADER_ROW}"}
            if source is not None and source.attrib.get("s"):
                attrs["s"] = source.attrib["s"]
            cell = ET.Element(_tag("c"), attrs)
            header.append(cell)
            header_cells[column] = cell
        _set_inline(cell, label)

    template_row = rows.get(FIRST_DATA_ROW)
    if template_row is None:
        raise ValueError("变压器Sheet缺少首条数据样式行")
    source_styles = _cell_map(template_row)
    numeric_style = source_styles.get("I")
    result_style = source_styles.get("U")
    cell_styles = {column: (result_style.attrib.get("s") if column == "U" and result_style is not None
                            else numeric_style.attrib.get("s") if column in "VWXY" and numeric_style is not None
                            else cell.attrib.get("s"))
                   for column, cell in source_styles.items()}
    for column in "VWXY":
        cell_styles[column] = numeric_style.attrib.get("s") if numeric_style is not None else None
    cell_styles["U"] = result_style.attrib.get("s") if result_style is not None else None
    cell_styles.update(J=loss_style, K=loss_style)

    for number in range(FIRST_DATA_ROW, LAST_DATA_ROW + 1):
        row = rows.get(number)
        if row is None:
            row = _row_from_template(template_row, number, cell_styles)
            rows[number] = row
            continue
        cells = _cell_map(row)
        # The original ten-row table has a sparse following row. Reusing that
        # row must still supply unlocked input styles for every declared column.
        for column, style in cell_styles.items():
            if column not in cells and _column_number(column) <= 25:
                cell = _blank_cell(f"{column}{number}", style)
                row.append(cell)
                cells[column] = cell
        for column in ("J", "K"):
            if column in cells:
                cells[column].set("s", loss_style)
        formula = f'IF(COUNTA(B{number}:K{number},S{number}:T{number},V{number}:Y{number})>0,ROW()-3,"")'
        existing_index = list(row).index(cells["A"]) if "A" in cells else 0
        if "A" in cells:
            row.remove(cells["A"])
        row.insert(existing_index, _formula_cell(
            f"A{number}", cell_styles.get("A"), formula))
        for column in "UVWXY":
            old = cells.get(column)
            if old is not None:
                row.remove(old)
        additions = [
            _blank_cell(f"{column}{number}", cell_styles.get(column))
            for column in "UVWXY"
        ]
        for cell in additions:
            row.append(cell)
        row.attrib["spans"] = "1:25"

    # Sort each row by cell coordinate; the row remains otherwise untouched.
    for row in rows.values():
        children = list(row.findall(_tag("c")))
        for child in children:
            row.remove(child)
        children.sort(key=lambda cell: _column_number(
            re.match(r"([A-Z]+)", cell.attrib["r"]).group(1)))
        row.extend(children)
    for row in list(sheet_data.findall(_tag("row"))):
        sheet_data.remove(row)
    sheet_data.extend(rows[number] for number in sorted(rows))

    # Replace the legacy category/condition validations with current contract lists.
    data_validations = root.find(_tag("dataValidations"))
    if data_validations is None:
        data_validations = ET.Element(_tag("dataValidations"))
        root.append(data_validations)
    existing = list(data_validations.findall(_tag("dataValidation")))
    by_range: dict[str, ET.Element] = {}
    for validation in existing:
        sqref = validation.attrib.get("sqref", "")
        first = sqref.split(":", 1)[0]
        match = re.match(r"([A-Z]+)", first)
        if not match:
            continue
        column = match.group(1)
        if column in "DFGHIJK":
            validation.attrib["sqref"] = f"{column}{FIRST_DATA_ROW}:{column}{LAST_DATA_ROW}"
            if column in "JK":
                validation.attrib["operator"] = "greaterThanOrEqual"
                formula = validation.find(_tag("formula1"))
                if formula is not None:
                    formula.text = "0"
            if column == "H":
                formula = validation.find(_tag("formula1"))
                if formula is not None:
                    formula.text = ('INDIRECT("EV_TR_COND_"&SUBSTITUTE('
                                    'INDEX(EV_TRANSFORMER_CATEGORY_IDS,'
                                    'MATCH($F4,EV_TRANSFORMER_CATEGORY,0)),"-","_"))')
                validation.attrib["allowBlank"] = "1"
                for attr in ("errorTitle", "error", "promptTitle", "prompt"):
                    validation.attrib.pop(attr, None)
                validation.set("showErrorMessage", "1")
                validation.set("errorTitle", "标准条件")
                validation.set("error", "请选择与设备实际结构一致的标准条件；不得手选损耗组。")
                validation.set("showInputMessage", "1")
                validation.set("promptTitle", "标准条件")
                validation.set("prompt", "仅填写适用的实际铁心、联结、热等级或新能源用途。")
            by_range[column] = validation
    for validation in existing:
        if validation not in by_range.values():
            data_validations.remove(validation)

    def add_decimal_validation(column: str, *, operator: str = "greaterThan") -> None:
        validation = ET.Element(_tag("dataValidation"), {
            "type": "decimal", "operator": operator, "allowBlank": "1",
            "showErrorMessage": "1",
            "sqref": f"{column}{FIRST_DATA_ROW}:{column}{LAST_DATA_ROW}",
        })
        ET.SubElement(validation, _tag("formula1")).text = "0"
        data_validations.append(validation)

    for column in "IVWXY":
        add_decimal_validation(column)
    data_validations.attrib["count"] = str(len(data_validations.findall(_tag("dataValidation"))))

    return _xml_bytes(root)


def _set_config_cell(rows: dict[int, ET.Element], column: int,
                     row_number: int, value: str) -> None:
    row = rows.get(row_number)
    if row is None:
        row = ET.Element(_tag("row"), {"r": str(row_number)})
        rows[row_number] = row
    reference = f"{_column_letters(column)}{row_number}"
    cells = _cell_map(row)
    cell = cells.get(_column_letters(column))
    if cell is None:
        cell = ET.Element(_tag("c"), {"r": reference})
        row.append(cell)
    _set_inline(cell, value)


def _patch_configuration(xml: bytes, categories: tuple[Any, ...]) -> bytes:
    root = _parse_xml(xml)
    sheet_data = root.find(_tag("sheetData"))
    if sheet_data is None:
        raise ValueError("配置Sheet缺少sheetData")
    rows = {int(row.attrib["r"]): row for row in sheet_data.findall(_tag("row"))
            if row.attrib.get("r", "").isdigit()}

    category_column = _column_number("R")
    id_column = _column_number("DK")
    condition_column = TRANSFORMER_CONDITION_FIRST_COLUMN
    for row_number in range(2, 62):
        _set_config_cell(rows, category_column, row_number, "")
        _set_config_cell(rows, id_column, row_number, "")
        for index in range(len(categories)):
            _set_config_cell(rows, condition_column + index, row_number, "")
    for col in LEGACY_CONDITION_COLUMNS:
        for row_number in range(2, 30):
            _set_config_cell(rows, col, row_number, "")

    for index, option in enumerate(categories):
        row_number = 2 + index
        category_id = _category_id(option)
        _set_config_cell(rows, category_column, row_number, _option_label(option))
        _set_config_cell(rows, id_column, row_number, category_id)
        for condition_index, condition in enumerate(_condition_options(category_id)):
            _set_config_cell(rows, condition_column + index, 2 + condition_index,
                             _option_label(condition))

    for row in rows.values():
        cells = list(row.findall(_tag("c")))
        for cell in cells:
            row.remove(cell)
        cells.sort(key=lambda cell: _column_number(
            re.match(r"([A-Z]+)", cell.attrib["r"]).group(1)))
        row.extend(cells)
    for row in list(sheet_data.findall(_tag("row"))):
        sheet_data.remove(row)
    sheet_data.extend(rows[number] for number in sorted(rows))

    cols = root.find(_tag("cols"))
    if cols is None:
        cols = ET.Element(_tag("cols"))
        sheet_data_index = list(root).index(sheet_data)
        root.insert(sheet_data_index, cols)
    first_hidden = id_column
    last_hidden = condition_column + len(categories) - 1
    merged: list[ET.Element] = []
    for col in list(cols.findall(_tag("col"))):
        min_col = int(col.attrib.get("min", "0"))
        max_col = int(col.attrib.get("max", "0"))
        if min_col <= last_hidden and max_col >= first_hidden:
            cols.remove(col)
        else:
            merged.append(col)
    ET.SubElement(cols, _tag("col"), {
        "min": str(first_hidden), "max": str(last_hidden),
        "width": "10", "hidden": "1", "customWidth": "1",
    })
    return _xml_bytes(root)


def _patch_workbook(xml: bytes, categories: tuple[Any, ...]) -> bytes:
    root = _parse_xml(xml)
    defined = root.find(_tag("definedNames"))
    if defined is None:
        defined = ET.SubElement(root, _tag("definedNames"))
    for node in list(defined.findall(_tag("definedName"))):
        name = node.attrib.get("name", "")
        if (name == "EV_TRANSFORMER_CATEGORY" or name == "EV_TRANSFORMER_CATEGORY_IDS"
                or name.startswith("EV_TR_COND_") or name in identity_defined_names(V61_TEMPLATE_ENTRY)):
            defined.remove(node)

    refs = {
        "EV_TRANSFORMER_CATEGORY": "'配置'!$R$2:$R$38",
        "EV_TRANSFORMER_CATEGORY_IDS": "'配置'!$DK$2:$DK$38",
    }
    category_ids = tuple(_category_id(item) for item in categories)
    for index, category_id in enumerate(category_ids):
        column = _column_letters(TRANSFORMER_CONDITION_FIRST_COLUMN + index)
        options = _condition_options(category_id)
        last_row = max(2, 1 + len(options))
        name = "EV_TR_COND_" + category_id.replace("-", "_")
        refs[name] = f"'配置'!${column}$2:${column}${last_row}"
    refs["EV_TR_COND_NONE"] = "'配置'!$DM$1:$DM$1"
    for name, reference in refs.items():
        ET.SubElement(defined, _tag("definedName"), {"name": name}).text = reference

    for name, value in identity_defined_names(V61_TEMPLATE_ENTRY).items():
        ET.SubElement(defined, _tag("definedName"), {"name": name}).text = (
            '"' + value.replace('"', '""') + '"')
    return _xml_bytes(root)


def _patch_table(xml: bytes) -> bytes:
    root = _parse_xml(xml)
    root.attrib["ref"] = "A3:Y103"
    auto_filter = root.find(_tag("autoFilter"))
    if auto_filter is not None:
        auto_filter.attrib["ref"] = "A3:Y103"
    columns = root.find(_tag("tableColumns"))
    if columns is None:
        raise ValueError("TblTransformer缺少tableColumns")
    columns.attrib["count"] = "25"
    table_columns = list(columns.findall(_tag("tableColumn")))
    if len(table_columns) != 21:
        raise ValueError(f"TblTransformer原始列数不是21：{len(table_columns)}")
    names = [
        "序号", "设备名称", "型号", "数量", "安装位置", "设备类别", "额定容量\n(kVA)",
        "标准条件", HEADERS["I"], HEADERS["J"], HEADERS["K"],
        "空载损耗-1级\n(W)", "空载损耗-2级\n(W)", "空载损耗-3级\n(W)",
        "负载损耗-1级\n(W)", "负载损耗-2级\n(W)", "负载损耗-3级\n(W)",
        "能效结论", "铭牌照片", "填表备注", HEADERS["U"],
        HEADERS["V"], HEADERS["W"], HEADERS["X"], HEADERS["Y"],
    ]
    for index, column in enumerate(table_columns):
        column.attrib["name"] = names[index]
        if index == 0:
            formula = column.find(_tag("calculatedColumnFormula"))
            if formula is not None:
                formula.text = ('IF(COUNTA(B4:K4,S4:T4,V4:Y4)>0,ROW()-3,"")')
        if index == 20:
            formula = column.find(_tag("calculatedColumnFormula"))
            if formula is not None:
                column.remove(formula)
    for index, label in enumerate(names[21:], start=22):
        ET.SubElement(columns, _tag("tableColumn"), {
            "id": str(index), "name": label,
        })
    return _xml_bytes(root)


def _loss_input_style(styles_xml: bytes, sheet_xml: bytes) -> tuple[bytes, str]:
    """Append a transformer-only decimal style; existing shared styles stay intact."""
    root = _parse_xml(styles_xml)
    formats = root.find(_tag("numFmts"))
    if formats is None:
        formats = ET.Element(_tag("numFmts"), {"count": "0"})
        root.insert(0, formats)
    format_id = max([163] + [int(x.attrib["numFmtId"]) for x in formats]) + 1
    ET.SubElement(formats, _tag("numFmt"), {
        "numFmtId": str(format_id), "formatCode": "0.###############"})
    formats.set("count", str(len(formats)))
    styles = root.find(_tag("cellXfs"))
    if styles is None:
        raise ValueError("模板缺少单元格样式")
    cell = _parse_xml(sheet_xml).find(f".//{_tag('c')}[@r='J4']")
    if cell is None:
        raise ValueError("模板缺少J4输入样式")
    style = deepcopy(styles[int(cell.attrib.get("s", "0"))])
    style.set("numFmtId", str(format_id))
    style.set("applyNumberFormat", "1")
    index = str(len(styles))
    styles.append(style)
    styles.set("count", str(len(styles)))
    return _xml_bytes(root), index


def _patch_transformer_instructions(xml: bytes) -> bytes:
    root = _parse_xml(xml)
    cell = root.find(f".//{_tag('c')}[@r='B13']")
    if cell is None:
        raise ValueError("模板说明缺少变压器说明B13")
    _set_inline(cell,
        "设备类别确定适用型式；标准条件选择铁心、热等级、联结组及新能源用途。"
        "表2仅630 kVA按I列额定阻抗选组，其他容量的阻抗只留记录；"
        "表27/28按I、X、Y三项额定阻抗选组，无需手选损耗组。"
        "损耗统一按W填写，保留小数。" + TRANSFORMER_SCOPE_HINT)
    row = root.find(f".//{_tag('row')}[@r='13']")
    if row is not None:
        row.set("ht", "108")
        row.set("customHeight", "1")
    return _xml_bytes(root)


def _patch_archive(source: Path, output: Path) -> None:
    categories = tuple(TRANSFORMER_CATEGORIES)
    if len(categories) != 37:
        raise ValueError(f"变压器受控类别应为37项，实际为{len(categories)}")
    if len({_category_id(item) for item in categories}) != len(categories):
        raise ValueError("变压器类别稳定ID重复")
    if len({_option_label(item) for item in categories}) != len(categories):
        raise ValueError("变压器类别显示标签重复")

    with ZipFile(source) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
        transformer_path = _sheet_target(archive, TRANSFORMER_SHEET)
        config_path = _sheet_target(archive, CONFIG_SHEET)
        table_path = _sheet_table_target(archive, transformer_path, "TblTransformer")
        instructions_path = _sheet_target(archive, "模板说明")
        transformer_xml = archive.read(transformer_path)
        styles_xml, loss_style = _loss_input_style(archive.read("xl/styles.xml"), transformer_xml)

    replacements = {
        transformer_path: _patch_transformer_sheet(transformer_xml, loss_style),
        "xl/styles.xml": styles_xml,
        instructions_path: _patch_transformer_instructions(
            next(data for info, data in entries if info.filename == instructions_path)),
        config_path: _patch_configuration(
            next(data for info, data in entries if info.filename == config_path), categories),
        "xl/workbook.xml": _patch_workbook(
            next(data for info, data in entries if info.filename == "xl/workbook.xml"), categories),
        table_path: _patch_table(
            next(data for info, data in entries if info.filename == table_path)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for info, data in entries:
            archive.writestr(info, replacements.get(info.filename, data))


def build(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT,
          *, update_manifest: bool = True) -> tuple[str, int]:
    source, output = Path(source), Path(output)
    if not source.is_file():
        raise SystemExit(f"找不到正式V6模板：{source}")
    expected_source_hash = str(V61_TEMPLATE_ENTRY["source_sha256"]).upper()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
    if source_hash != expected_source_hash:
        raise SystemExit(
            "V6.1派生源不是清单登记的正式V6资产；拒绝生成。\n"
            f"期望 {expected_source_hash}\n实际 {source_hash}")
    if source.resolve() == output.resolve():
        raise SystemExit("V6.1输出不得覆盖V6输入模板")
    _patch_archive(source, output)
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    output_size = output.stat().st_size
    if update_manifest:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        entry = next(item for item in manifest["templates"]
                     if item.get("template_version") == "V6.1")
        entry["asset_sha256"] = output_hash
        entry["asset_size_bytes"] = output_size
        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    return output_hash, output_size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-update-manifest", action="store_true")
    args = parser.parse_args(argv)
    digest, size = build(args.source, args.output,
                         update_manifest=not args.no_update_manifest)
    print(f"V6.1模板: {args.output}")
    print(f"SHA-256: {digest}")
    print(f"大小: {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
