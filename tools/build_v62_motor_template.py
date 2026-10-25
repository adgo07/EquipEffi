"""从已登记的V6.1候选模板派生V6.2电动机模板。

仅补丁电动机Sheet、模板说明/注意事项、配置Sheet和身份/样式依赖；其余ZIP
部件按原始字节复制。电动机枚举与条件字段直接读取Domain input contract。
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from equipeffi.domain.devices.motor.input_contract import (  # noqa: E402
    BASIS_OPTIONS,
    MOTOR_CATEGORIES,
    scope_hint,
    test_basis_hint,
    visible_fields,
)
from equipeffi.infrastructure.excel.template_resource import (  # noqa: E402
    TEMPLATE_MANIFEST,
    V61_TEMPLATE_ENTRY,
    V61_TEMPLATE_IDENTITY,
    identity_defined_names,
)
from build_v61_transformer_template import (  # noqa: E402
    CONFIG_SHEET,
    FIRST_DATA_ROW,
    HEADER_ROW,
    LAST_DATA_ROW,
    MAIN_NS,
    _cell_map,
    _column_letters,
    _column_number,
    _parse_xml,
    _sheet_target,
    _sheet_table_target,
    _set_config_cell,
    _set_inline,
    _tag,
    _xml_bytes,
)


DEFAULT_SOURCE = ROOT / "src" / "equipeffi" / "resources" / "templates" / V61_TEMPLATE_IDENTITY["filename"]
DEFAULT_OUTPUT_NAME = "设备能效分析空白模板_重构版V6_2.xlsx"
DEFAULT_OUTPUT = ROOT / "src" / "equipeffi" / "resources" / "templates" / DEFAULT_OUTPUT_NAME
MANIFEST_PATH = ROOT / "src" / "equipeffi" / "resources" / "TEMPLATE_MANIFEST.json"
V62_TEMPLATE_ID = "equipeffi.device-efficiency.V6.2"

MOTOR_SHEET = "电动机"
INSTRUCTIONS_SHEET = "注意事项"
TEMPLATE_NOTES_SHEET = "模板说明"
FIRST_CONFIG_COLUMN = _column_number("EW")
MOTOR_CATEGORY_COLUMN = _column_number("EW")
MOTOR_CATEGORY_ID_COLUMN = _column_number("EX")
MOTOR_BASIS_COLUMN = _column_number("FG")
MOTOR_CONFIG_LAST_COLUMN = MOTOR_BASIS_COLUMN
MOTOR_CATEGORY_NAME = "EV_MOTOR_V62_CATEGORY"
MOTOR_CATEGORY_IDS_NAME = "EV_MOTOR_V62_CATEGORY_IDS"
MOTOR_BASIS_NAME = "EV_MOTOR_V62_BASIS"
MOTOR_INPUT_ROWS = range(FIRST_DATA_ROW, LAST_DATA_ROW + 1)
DECIMAL_FORMAT = "0.###############"

# Excel input controls only; the Application contract owns business validation.
MOTOR_EXCEL_VALIDATIONS = {
    "rated_frequency_hz": {
        "column": "H", "type": "custom",
        "formula1": 'OR(H4="",ISNUMBER(H4),ISTEXT(H4))',
        "error_title": "额定频率",
        "error": "额定频率可填写数字或文本范围，请保留原始文本。",
        "prompt_title": "额定频率",
        "prompt": "可填数字或原始文本范围，如5~120；表1—4由软件核对范围，表5/6仅留痕。",
    },
    "poles": {
        "column": "K", "type": "custom",
        "formula1": 'OR(K4="",AND(ISNUMBER(K4),K4>0,MOD(K4,2)=0))',
        "error_title": "极数",
        "error": "极数应填写正偶数。",
        "prompt_title": "极数",
        "prompt": "填写任意正偶数；标准未覆盖值由软件判为不在范围，表6仅留痕。",
    },
}

LEGACY_MOTOR_DEFINED_NAMES = frozenset({
    "EV_MOTOR_CATEGORY", "EV_POLES_LV", "EV_POLES_HV", "EV_POLES_PMSM",
    "EV_MOTOR_VOLTAGE", "EV_COOLING_MOTOR_HV", "EV_COOLING_PMSM",
})

HEADERS = {
    "A": "序号",
    "B": "设备名称",
    "C": "型号",
    "D": "数量",
    "E": "安装位置",
    "F": "设备类别",
    "G": "额定电压\n(kV)",
    "H": "额定频率\n(Hz)",
    "I": "实测效率口径说明",
    "J": "额定输出功率\n(kW)",
    "K": "极数\n(极)",
    "L": "铭牌标称最高转速\n(r/min)",
    "M": "额定输出功率下实测效率\n(%)",
    "N": "1级效率阈值\n(%)",
    "O": "2级效率阈值\n(%)",
    "P": "3级效率阈值\n(%)",
    "Q": "能效等级",
    "R": "铭牌照片",
    "S": "填表备注",
    "T": "评价说明",
}

OUTPUT_AREA_LABELS = (
    "本次批量处理说明",
    "模板版本",
    "处理时间",
    "已评价Sheet",
    "未评价Sheet",
    "统计口径",
    "未评价提示",
    "软件区域标识",
)


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


def _category_id(option: Any) -> str:
    value = _field(option, "category_id")
    if value is None:
        raise ValueError(f"电动机类别缺少稳定ID：{option!r}")
    return str(value)


def _category_label(option: Any) -> str:
    value = _field(option, "label")
    if value is None:
        raise ValueError(f"电动机类别缺少显示名称：{option!r}")
    return str(value)


def _all_motor_field_ids() -> tuple[str, ...]:
    return (
        "rated_voltage_kv", "rated_frequency_hz", "efficiency_basis_status",
        "rated_output_power_kw", "poles", "max_nameplate_speed_rpm",
        "measured_efficiency_pct", "user_note",
    )


def _motor_sheet_contract() -> dict[str, Any]:
    category_ids = tuple(_category_id(item) for item in MOTOR_CATEGORIES)
    fields: list[dict[str, Any]] = [
        {"column": "A", "role": "index", "label": HEADERS["A"]},
        {"column": "B", "role": "input", "field_id": "device_name", "label": HEADERS["B"]},
        {"column": "C", "role": "input", "field_id": "model", "label": HEADERS["C"]},
        {"column": "D", "role": "input", "field_id": "quantity", "label": HEADERS["D"]},
        {"column": "E", "role": "input", "field_id": "location", "label": HEADERS["E"]},
        {"column": "F", "role": "input", "field_id": "category_id", "label": HEADERS["F"],
         "category_enum": MOTOR_CATEGORY_NAME},
    ]
    column_by_field = {
        "rated_voltage_kv": "G", "rated_frequency_hz": "H",
        "efficiency_basis_status": "I", "rated_output_power_kw": "J",
        "poles": "K", "max_nameplate_speed_rpm": "L",
        "measured_efficiency_pct": "M", "user_note": "S",
    }
    domain_fields: dict[str, Any] = {}
    for category_id in category_ids:
        for field in visible_fields(category_id):
            domain_fields.setdefault(field.field_id, field)
    for field_id in _all_motor_field_ids():
        if field_id not in domain_fields and field_id != "user_note":
            continue
        descriptor = domain_fields.get(field_id)
        required_categories = [
            category_id for category_id in category_ids
            if any(item.field_id == field_id and item.required
                   for item in visible_fields(category_id))
        ]
        if field_id == "user_note":
            label, unit = "填表备注", None
        else:
            label = descriptor.label
            unit = descriptor.unit
        field: dict[str, Any] = {
            "column": column_by_field[field_id], "role": "input",
            "field_id": field_id, "label": label,
            "required_for_categories": required_categories,
        }
        if unit:
            field["unit"] = unit
        if field_id == "efficiency_basis_status":
            field["defined_name"] = MOTOR_BASIS_NAME
        if field_id in MOTOR_EXCEL_VALIDATIONS:
            field["excel_validation"] = dict(MOTOR_EXCEL_VALIDATIONS[field_id])
        fields.append(field)
    fields.extend([
        {"column": "N", "role": "result", "label": "1级效率阈值", "unit": "%",
         "threshold_key": "grade_1"},
        {"column": "O", "role": "result", "label": "2级效率阈值", "unit": "%",
         "threshold_key": "grade_2"},
        {"column": "P", "role": "result", "label": "3级效率阈值", "unit": "%",
         "threshold_key": "grade_3"},
        {"column": "Q", "role": "result", "label": "能效等级", "result_key": "conclusion"},
        {"column": "R", "role": "input", "field_id": "photo", "label": "铭牌照片"},
        {"column": "T", "role": "result", "label": "评价说明", "result_key": "messages"},
    ])
    # Keep the displayed column sequence canonical (A:T), including user_note at S.
    fields.sort(key=lambda item: _column_number(str(item["column"])))
    return {
        "sheet_id": "motor", "sheet_name": MOTOR_SHEET,
        "contract_revision": "motor-input.v2", "status": "CONNECTED",
        "header_row": 3,
        "table": {"name": "TblMotor", "ref": "A3:T103"},
        "fields": fields,
        "categories": [
            {"category_id": _category_id(item), "label": _category_label(item),
             "table_no": _field(item, "table_no")}
            for item in MOTOR_CATEGORIES
        ],
        "category_ids": list(category_ids),
    }


def _add_decimal_style(styles_xml: bytes, motor_xml: bytes) -> tuple[bytes, dict[str, str]]:
    root = _parse_xml(styles_xml)
    num_fmts = root.find(_tag("numFmts"))
    if num_fmts is None:
        num_fmts = ET.Element(_tag("numFmts"), {"count": "0"})
        root.insert(0, num_fmts)
    format_node = next((node for node in num_fmts.findall(_tag("numFmt"))
                        if node.attrib.get("formatCode") == DECIMAL_FORMAT), None)
    if format_node is None:
        used = [int(node.attrib["numFmtId"]) for node in num_fmts.findall(_tag("numFmt"))
                if node.attrib.get("numFmtId", "").isdigit()]
        format_id = max([163, *used]) + 1
        ET.SubElement(num_fmts, _tag("numFmt"), {
            "numFmtId": str(format_id), "formatCode": DECIMAL_FORMAT,
        })
    else:
        format_id = int(format_node.attrib["numFmtId"])
    num_fmts.set("count", str(len(num_fmts.findall(_tag("numFmt")))))

    styles = root.find(_tag("cellXfs"))
    if styles is None:
        raise ValueError("模板缺少单元格样式定义")
    motor_root = _parse_xml(motor_xml)
    cells = {cell.attrib.get("r", ""): cell
             for cell in motor_root.findall(f".//{_tag('sheetData')}/{_tag('row')}/{_tag('c')}")}
    style_ids: dict[str, str] = {}
    cached: dict[str, str] = {}
    for column in ("G", "H", "J", "L", "M", "N", "O", "P"):
        reference = f"{column}4"
        cell = cells.get(reference)
        if cell is None:
            raise ValueError(f"电动机模板缺少样式来源：{reference}")
        original_id = cell.attrib.get("s", "0")
        cache_key = f"{original_id}:{format_id}"
        style_id = cached.get(cache_key)
        if style_id is None:
            style = deepcopy(styles[int(original_id)])
            style.set("numFmtId", str(format_id))
            style.set("applyNumberFormat", "1")
            style_id = str(len(styles))
            styles.append(style)
            cached[cache_key] = style_id
        style_ids[column] = style_id
    styles.set("count", str(len(styles)))
    return _xml_bytes(root), style_ids


def _set_formula(cell: ET.Element, formula: str) -> None:
    for child in list(cell):
        if child.tag in {_tag("f"), _tag("v"), _tag("is")}:
            cell.remove(child)
    cell.attrib.pop("t", None)
    ET.SubElement(cell, _tag("f")).text = formula
    ET.SubElement(cell, _tag("v"))


def _clear_formula(cell: ET.Element) -> None:
    for child in list(cell):
        if child.tag in {_tag("f"), _tag("v"), _tag("is")}:
            cell.remove(child)
    cell.attrib.pop("t", None)


def _motor_validation(column: str, kind: str, formula1: str, *,
                      operator: str | None = None, formula2: str | None = None,
                      error_title: str, error: str,
                      prompt_title: str, prompt: str) -> ET.Element:
    attrs = {
        "type": kind, "allowBlank": "1", "showErrorMessage": "1",
        "showInputMessage": "1", "sqref": f"{column}{FIRST_DATA_ROW}:{column}{LAST_DATA_ROW}",
        "errorStyle": "stop", "showDropDown": "0",
        "errorTitle": error_title, "error": error,
        "promptTitle": prompt_title, "prompt": prompt,
    }
    if operator:
        attrs["operator"] = operator
    node = ET.Element(_tag("dataValidation"), attrs)
    ET.SubElement(node, _tag("formula1")).text = formula1
    if formula2 is not None:
        ET.SubElement(node, _tag("formula2")).text = formula2
    return node


def _configured_motor_validation(field_id: str) -> ET.Element:
    rule = MOTOR_EXCEL_VALIDATIONS[field_id]
    return _motor_validation(
        str(rule["column"]), str(rule["type"]), str(rule["formula1"]),
        error_title=str(rule["error_title"]), error=str(rule["error"]),
        prompt_title=str(rule["prompt_title"]), prompt=str(rule["prompt"]))


def _patch_motor_sheet(xml: bytes, decimal_styles: dict[str, str]) -> bytes:
    root = _parse_xml(xml)
    dimension = root.find(_tag("dimension"))
    if dimension is not None:
        dimension.set("ref", "A1:T103")
    rows = root.find(_tag("sheetData"))
    if rows is None:
        raise ValueError("电动机Sheet缺少sheetData")
    by_row = {int(row.attrib["r"]): row for row in rows.findall(_tag("row"))
              if row.attrib.get("r", "").isdigit()}
    header = by_row.get(HEADER_ROW)
    if header is None:
        raise ValueError("电动机Sheet缺少第3行表头")
    title = by_row.get(1)
    title_cells = _cell_map(title) if title is not None else {}
    if title_cells.get("A") is None:
        raise ValueError("电动机Sheet缺少标题A1")
    _set_inline(title_cells["A"], "电动机 - GB 18613—2020《电动机能效限定值及能效等级》")
    header_cells = _cell_map(header)
    for column, label in HEADERS.items():
        cell = header_cells.get(column)
        if cell is None:
            raise ValueError(f"电动机Sheet缺少{column}3表头")
        _set_inline(cell, label)

    template_row = by_row.get(FIRST_DATA_ROW)
    if template_row is None:
        raise ValueError("电动机Sheet缺少首条输入样式行")
    template_cells = _cell_map(template_row)
    for number in MOTOR_INPUT_ROWS:
        row = by_row.get(number)
        if row is None:
            raise ValueError(f"电动机Sheet缺少预置数据行：{number}")
        cells = _cell_map(row)
        for column in ("G", "H", "J", "L", "M", "N", "O", "P"):
            cell = cells.get(column)
            if cell is None:
                source = template_cells.get(column)
                attrs = {"r": f"{column}{number}"}
                if source is not None and source.attrib.get("s"):
                    attrs["s"] = source.attrib["s"]
                cell = ET.Element(_tag("c"), attrs)
                row.append(cell)
                cells[column] = cell
            cell.set("s", decimal_styles[column])
        index_cell = cells.get("A")
        if index_cell is None:
            raise ValueError(f"电动机Sheet缺少序号单元格：A{number}")
        _set_formula(index_cell,
                     f'IF(COUNTA(B{number}:M{number},R{number}:S{number})>0,ROW()-3,"")')
        legacy_note = cells.get("T")
        if legacy_note is None:
            raise ValueError(f"电动机Sheet缺少旧自动备注单元格：T{number}")
        if legacy_note.find(_tag("f")) is None:
            raise ValueError(f"电动机Sheet T{number}未发现待退役公式")
        _clear_formula(legacy_note)

    # Keep column order valid after adding missing styled numeric cells.
    for row in by_row.values():
        cells = list(row.findall(_tag("c")))
        for cell in cells:
            row.remove(cell)
        cells.sort(key=lambda cell: _column_number(
            re.match(r"([A-Z]+)", cell.attrib["r"]).group(1)))
        row.extend(cells)

    data_validations = root.find(_tag("dataValidations"))
    if data_validations is None:
        data_validations = ET.Element(_tag("dataValidations"))
        root.append(data_validations)
    for node in list(data_validations.findall(_tag("dataValidation"))):
        data_validations.remove(node)
    data_validations.extend([
        _motor_validation("D", "whole", "0", operator="greaterThan",
                          error_title="数量", error="数量必须为大于0的正整数。",
                          prompt_title="数量", prompt="数量必填，按正整数填写。"),
        _motor_validation("F", "list", MOTOR_CATEGORY_NAME,
                          error_title="设备类别", error="请选择GB 18613已登记的六类、其他类别或不确定类别。",
                          prompt_title="设备类别", prompt="按实际类型明确选择；不按型号或备注推断。"),
        _motor_validation("G", "decimal", "0", operator="greaterThanOrEqual",
                          error_title="额定电压", error="额定电压请按kV填写非负数值。",
                          prompt_title="额定电压", prompt="表1—4按类别填写；表5/6不以电压选表。"),
        _configured_motor_validation("rated_frequency_hz"),
        _motor_validation("I", "list", MOTOR_BASIS_NAME,
                          error_title="效率口径说明", error="请选择已登记的效率口径说明。",
                          prompt_title="效率口径说明", prompt="留空表示按M列口径填报，不代表试验报告已核验。"),
        _motor_validation("J", "decimal", "0", operator="greaterThan",
                          error_title="额定输出功率", error="额定输出功率必须大于0。",
                          prompt_title="额定输出功率", prompt="统一使用kW，例如10 W填0.010，750 W填0.750。"),
        _configured_motor_validation("poles"),
        _motor_validation("L", "decimal", "0", operator="greaterThanOrEqual",
                          error_title="铭牌标称最高转速", error="转速请填写非负数值。",
                          prompt_title="铭牌标称最高转速", prompt="表6必填；其他类别不按该值选表。"),
        _motor_validation("M", "decimal", "1", operator="between", formula2="100",
                          error_title="实测效率", error="请输入1至100之间的百分数点值，例如85.9；不要输入0.859或百分比格式。",
                          prompt_title="实测效率", prompt="按额定输出功率工况填写百分数点值，保留小数。"),
    ])
    data_validations.set("count", str(len(data_validations.findall(_tag("dataValidation")))))
    return _xml_bytes(root)


def _patch_motor_table(xml: bytes) -> bytes:
    root = _parse_xml(xml)
    root.set("ref", "A3:T103")
    auto_filter = root.find(_tag("autoFilter"))
    if auto_filter is not None:
        auto_filter.set("ref", "A3:T103")
    columns = root.find(_tag("tableColumns"))
    if columns is None:
        raise ValueError("TblMotor缺少tableColumns")
    table_columns = list(columns.findall(_tag("tableColumn")))
    if len(table_columns) != 20:
        raise ValueError(f"TblMotor原始列数不是20：{len(table_columns)}")
    columns.set("count", "20")
    for index, column in enumerate(table_columns):
        letter = _column_letters(index + 1)
        column.set("name", HEADERS[letter].replace("\n", "\n"))
        formula = column.find(_tag("calculatedColumnFormula"))
        if letter == "A":
            if formula is None:
                formula = ET.SubElement(column, _tag("calculatedColumnFormula"))
            formula.text = 'IF(COUNTA(B4:M4,R4:S4)>0,ROW()-3,"")'
        elif letter == "T" and formula is not None:
            column.remove(formula)
    return _xml_bytes(root)


def _config_rows(xml: bytes) -> tuple[ET.Element, ET.Element, dict[int, ET.Element]]:
    root = _parse_xml(xml)
    sheet_data = root.find(_tag("sheetData"))
    if sheet_data is None:
        raise ValueError("配置Sheet缺少sheetData")
    rows = {int(row.attrib["r"]): row for row in sheet_data.findall(_tag("row"))
            if row.attrib.get("r", "").isdigit()}
    return root, sheet_data, rows


def _patch_configuration(xml: bytes) -> bytes:
    root, sheet_data, rows = _config_rows(xml)
    categories = tuple(MOTOR_CATEGORIES)
    if len(categories) != 8:
        raise ValueError(f"GB18613电动机类别应为8项，实际为{len(categories)}")
    category_ids = tuple(_category_id(item) for item in categories)
    labels = tuple(_category_label(item) for item in categories)
    if len(set(category_ids)) != 8 or len(set(labels)) != 8:
        raise ValueError("GB18613电动机类别ID和显示标签必须唯一")

    # V6.1的配置数据保持原值；V6.2类别与效率口径枚举位于独立区域。
    for offset, option in enumerate(categories):
        row_number = 2 + offset
        _set_config_cell(rows, MOTOR_CATEGORY_COLUMN, row_number, _category_label(option))
        _set_config_cell(rows, MOTOR_CATEGORY_ID_COLUMN, row_number, _category_id(option))
    for option_index, (_value, label) in enumerate(BASIS_OPTIONS):
        _set_config_cell(rows, MOTOR_BASIS_COLUMN, 2 + option_index, label)

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
        root.insert(list(root).index(sheet_data), cols)
    for node in list(cols.findall(_tag("col"))):
        lower = int(node.attrib.get("min", "0"))
        upper = int(node.attrib.get("max", "0"))
        if lower <= MOTOR_CONFIG_LAST_COLUMN and upper >= FIRST_CONFIG_COLUMN:
            cols.remove(node)
    ET.SubElement(cols, _tag("col"), {
        "min": str(FIRST_CONFIG_COLUMN), "max": str(MOTOR_CONFIG_LAST_COLUMN),
        "width": "10", "hidden": "1", "customWidth": "1",
    })
    dimension = root.find(_tag("dimension"))
    if dimension is not None:
        prior = str(dimension.attrib.get("ref", "A1"))
        last_row_match = re.search(r":?[A-Z]{1,3}(\d+)$", prior)
        last_row = int(last_row_match.group(1)) if last_row_match else 2 + len(BASIS_OPTIONS)
        dimension.set("ref", f"A1:{_column_letters(MOTOR_CONFIG_LAST_COLUMN)}{max(last_row, 2 + len(categories))}")
    return _xml_bytes(root)


def _motor_defined_names() -> dict[str, str]:
    return {
        MOTOR_CATEGORY_NAME: "'配置'!$EW$2:$EW$9",
        MOTOR_CATEGORY_IDS_NAME: "'配置'!$EX$2:$EX$9",
        MOTOR_BASIS_NAME: f"'配置'!$FG$2:$FG${1 + len(BASIS_OPTIONS)}",
    }


def _identity_names(entry: dict[str, Any]) -> set[str]:
    return set(identity_defined_names(entry))


def _patch_workbook(xml: bytes, entry: dict[str, Any]) -> bytes:
    root = _parse_xml(xml)
    defined = root.find(_tag("definedNames"))
    if defined is None:
        defined = ET.SubElement(root, _tag("definedNames"))
    old_identity = _identity_names(V61_TEMPLATE_ENTRY)
    for node in list(defined.findall(_tag("definedName"))):
        name = node.attrib.get("name", "")
        if (name in LEGACY_MOTOR_DEFINED_NAMES
                or name.startswith("EV_MOTOR_V62_")
                or name in old_identity):
            defined.remove(node)
    for name, reference in _motor_defined_names().items():
        ET.SubElement(defined, _tag("definedName"), {"name": name}).text = reference
    for name, value in identity_defined_names(entry).items():
        ET.SubElement(defined, _tag("definedName"), {"name": name}).text = (
            '"' + value.replace('"', '""') + '"')
    return _xml_bytes(root)


def _insert_notes_cell(rows: dict[int, ET.Element], row_number: int,
                       column: str, value: str, style: str | None) -> None:
    row = rows.get(row_number)
    if row is None:
        row = ET.Element(_tag("row"), {"r": str(row_number), "spans": "1:8"})
        rows[row_number] = row
    cells = _cell_map(row)
    cell = cells.get(column)
    if cell is None:
        attrs = {"r": f"{column}{row_number}"}
        if style:
            attrs["s"] = style
        cell = ET.Element(_tag("c"), attrs)
        row.append(cell)
    _set_inline(cell, value)


def _motor_guidance_text() -> tuple[str, str]:
    category_text = "；".join(
        f"{_category_label(category)}：{scope_hint(_category_id(category))}"
        for category in MOTOR_CATEGORIES if _field(category, "table_no") is not None)
    basis_text = "；".join(
        f"{_category_label(category)}：{test_basis_hint(_category_id(category))}"
        for category in MOTOR_CATEGORIES if _field(category, "table_no") is not None)
    detail = (
        "电动机仅接入GB 18613—2020六类；类别按实际结构明确选择，不从型号或备注推断。"
        "额定功率统一按kW、额定电压按kV，频率按Hz填写；效率填额定功率工况实测百分数点值1～100，"
        "例如85.9，不输入0.859或百分比格式。10 W填0.010 kW，750 W填0.750 kW。"
        "表1—4按适用条件填写电压、50 Hz和极数，表5按极数选列，表6按铭牌标称最高转速选列；"
        "非适用字段可留空或填0留痕，不以其范围选表。I列留空表示按M列字段口径填报，"
        "不表示试验报告已经核验；其他口径问题按选项说明处理。\n"
        + category_text + "\n" + basis_text)
    summary = ("GB 18613—2020仅接通以下六类：" + category_text
               + " 实测效率按对应试验方法填报：" + basis_text)
    return detail, summary


def _patch_template_notes(xml: bytes) -> bytes:
    root = _parse_xml(xml)
    sheet_data = root.find(_tag("sheetData"))
    if sheet_data is None:
        raise ValueError("模板说明Sheet缺少sheetData")
    rows = {int(row.attrib["r"]): row for row in sheet_data.findall(_tag("row"))
            if row.attrib.get("r", "").isdigit()}
    motor_row = rows.get(21)
    motor_cells = _cell_map(motor_row) if motor_row is not None else {}
    motor_note = motor_cells.get("B")
    if motor_note is None:
        raise ValueError("模板说明Sheet缺少B21电动机输入说明")
    detail, _summary = _motor_guidance_text()
    _set_inline(motor_note, detail)
    motor_row.set("ht", "150")
    motor_row.set("customHeight", "1")
    existing = {f"{column}{number}": cell
                for number, row in rows.items()
                for column, cell in _cell_map(row).items()
                if 27 <= number <= 34 and column in {"A", "B"}}
    for reference, cell in existing.items():
        payload = cell.find(_tag("f")) is not None or cell.find(_tag("v")) is not None
        inline = cell.find(_tag("is"))
        text = "".join(node.text or "" for node in inline.iter(_tag("t"))) if inline is not None else ""
        if payload and (reference not in {f"A{row}" for row in range(27, 35)} or text):
            raise ValueError(f"V6.1模板说明输出区不是空白：{reference}")

    style_rows = rows.get(24)
    base_cells = _cell_map(style_rows) if style_rows is not None else {}
    a_style = base_cells.get("A").attrib.get("s") if base_cells.get("A") is not None else None
    b_style = base_cells.get("B").attrib.get("s") if base_cells.get("B") is not None else None
    labels = OUTPUT_AREA_LABELS
    for offset, label in enumerate(labels):
        row_number = 27 + offset
        _insert_notes_cell(rows, row_number, "A", label, a_style)
        _insert_notes_cell(rows, row_number, "B", "", b_style)
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
    for row_number, height in ((27, 22), (28, 20), (29, 20), (30, 28),
                               (31, 28), (32, 34), (33, 34), (34, 20)):
        rows[row_number].set("ht", str(height))
        rows[row_number].set("customHeight", "1")
    dimension = root.find(_tag("dimension"))
    if dimension is not None:
        dimension.set("ref", "A1:H34")
    return _xml_bytes(root)


def _patch_instructions(xml: bytes) -> bytes:
    root = _parse_xml(xml)
    _detail, summary = _motor_guidance_text()
    instructions = root.find(f".//{_tag('c')}[@r='H14']")
    if instructions is None:
        raise ValueError("注意事项Sheet缺少H14电动机范围摘要")
    _set_inline(instructions, summary)
    instruction_row = root.find(f".//{_tag('row')}[@r='14']")
    if instruction_row is not None:
        instruction_row.set("ht", "150")
        instruction_row.set("customHeight", "1")
    return _xml_bytes(root)


def _motor_manifest_entry(source_sha256: str, source_size: int) -> dict[str, Any]:
    entry = deepcopy(V61_TEMPLATE_ENTRY)
    entry.update({
        "template_id": V62_TEMPLATE_ID,
        "template_version": "V6.2",
        "template_kind": "unified-multi-device-blank-template",
        "template_contract_revision": "unified-v6.v3",
        "status": "CANDIDATE",
        "input_compatibility": "ACCEPTED",
        "legacy_import_compatibility": False,
        "filename": DEFAULT_OUTPUT_NAME,
        "asset_sha256": "",
        "asset_size_bytes": 0,
        "source_filename": V61_TEMPLATE_IDENTITY["filename"],
        "source_sha256": source_sha256,
        "source_size_bytes": source_size,
        "source_provenance": (
            "从清单登记的V6.1候选资产派生；泵/变压器Sheet、既有共享配置及其他Sheet保留，"
            "仅增加GB 18613电动机契约和批次说明区域。"),
        "authorized_modification": {
            "sheet": "电动机及其专属模板配置",
            "phase": "GB 18613—2020接入候选",
            "changes": [
                "仅连接GB 18613六类电动机以及其他类别/不确定类别；高压和永磁同步电机旧数据留在旧模板。",
                "保留20列，输入和结果由统一Application链处理；退出T4:T103旧自动评价公式。",
                "在独立配置区域新增电机类别和效率口径；极数改为正偶数输入，由统一Application判定标准覆盖；泵/变压器契约与既有共享枚举不变。",
            ],
        },
        "untouched_sheets": 14,
        "untouched_verification": (
            "tests/unit/test_v62_motor_template.py：泵/变压器Sheet及其他未授权Sheet的XML字节、"
            "既有配置值和泵/变压器命名范围逐项比对。"),
        "generated_by": "tools/build_v62_motor_template.py",
    })
    sheets = deepcopy(entry["sheets"])
    for item in sheets:
        if item.get("sheet_id") == "motor":
            item.clear()
            item.update(_motor_sheet_contract())
    entry["sheets"] = sheets
    config = deepcopy(entry.get("configuration_contract", {}))
    config.update({
        "motor_category_enum": {
            "column": "EW", "first_row": 2,
            "defined_name": MOTOR_CATEGORY_NAME,
            "category_ids_column": "EX",
            "category_ids_defined_name": MOTOR_CATEGORY_IDS_NAME,
        },
        "motor_efficiency_basis_enum": {
            "column": "FG", "first_row": 2,
            "defined_name": MOTOR_BASIS_NAME,
        },
        "motor_excel_validations": {
            field_id: dict(rule)
            for field_id, rule in MOTOR_EXCEL_VALIDATIONS.items()
        },
    })
    entry["configuration_contract"] = config
    entry["motor_capacity_strategy"] = {
        "mechanism": "Excel Table（TblMotor，20列×100条预置数据）+统一Reader",
        "user_action_required": "无：表格内继续填写或粘贴；Writer不会扩展T列旧公式。",
        "business_row_limit": "none",
        "manual_engine_validation": "NOT_RUN；Excel/WPS新增行、保存重开需单独记录。",
    }
    return entry


def _patch_archive(source: Path, output: Path) -> None:
    categories = tuple(MOTOR_CATEGORIES)
    if len(categories) != 8:
        raise ValueError(f"电动机受控类别应为8项，实际为{len(categories)}")
    with ZipFile(source) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
        motor_path = _sheet_target(archive, MOTOR_SHEET)
        config_path = _sheet_target(archive, CONFIG_SHEET)
        instructions_path = _sheet_target(archive, INSTRUCTIONS_SHEET)
        notes_path = _sheet_target(archive, TEMPLATE_NOTES_SHEET)
        table_path = _sheet_table_target(archive, motor_path, "TblMotor")
        motor_xml = archive.read(motor_path)
        styles_xml, decimal_styles = _add_decimal_style(
            archive.read("xl/styles.xml"), motor_xml)
        source_workbook_xml = archive.read("xl/workbook.xml")
        source_config_xml = archive.read(config_path)
        source_notes_xml = archive.read(notes_path)
        source_instructions_xml = archive.read(instructions_path)
        source_table_xml = archive.read(table_path)

    source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
    entry = _motor_manifest_entry(
        source_hash, source.stat().st_size)
    replacements = {
        motor_path: _patch_motor_sheet(motor_xml, decimal_styles),
        "xl/styles.xml": styles_xml,
        config_path: _patch_configuration(source_config_xml),
        instructions_path: _patch_instructions(source_instructions_xml),
        notes_path: _patch_template_notes(source_notes_xml),
        "xl/workbook.xml": _patch_workbook(source_workbook_xml, entry),
        table_path: _patch_motor_table(source_table_xml),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for info, data in entries:
            archive.writestr(info, replacements.get(info.filename, data))


def _update_manifest(output_hash: str, output_size: int,
                     source_hash: str, source_size: int) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = _motor_manifest_entry(source_hash, source_size)
    entry["asset_sha256"] = output_hash
    entry["asset_size_bytes"] = output_size
    previous = next((index for index, item in enumerate(manifest["templates"])
                     if item.get("template_version") == "V6.2"), None)
    if previous is None:
        source_index = next(index for index, item in enumerate(manifest["templates"])
                            if item.get("template_version") == "V6.1")
        manifest["templates"].insert(source_index + 1, entry)
    else:
        manifest["templates"][previous] = entry
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT,
          *, update_manifest: bool = True) -> tuple[str, int]:
    source, output = Path(source), Path(output)
    if not source.is_file():
        raise SystemExit(f"找不到登记的V6.1模板：{source}")
    expected_source_hash = str(V61_TEMPLATE_ENTRY["asset_sha256"]).upper()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
    if source_hash != expected_source_hash:
        raise SystemExit(
            "V6.2派生源不是清单登记的V6.1候选资产；拒绝生成。\n"
            f"期望 {expected_source_hash}\n实际 {source_hash}")
    if source.resolve() == output.resolve():
        raise SystemExit("V6.2输出不得覆盖V6.1输入模板")
    _patch_archive(source, output)
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    output_size = output.stat().st_size
    if update_manifest:
        _update_manifest(output_hash, output_size, source_hash, source.stat().st_size)
    return output_hash, output_size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-update-manifest", action="store_true")
    args = parser.parse_args(argv)
    digest, size = build(args.source, args.output,
                         update_manifest=not args.no_update_manifest)
    print(f"V6.2模板: {args.output}")
    print(f"SHA-256: {digest}")
    print(f"大小: {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
