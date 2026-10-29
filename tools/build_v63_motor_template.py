"""从登记的V6.2资产定点派生V6.3铭牌额定输入模板。

只改电动机Sheet、其Table、两处电机填写说明、styles.xml和工作簿身份标记；
泵、变压器、共享配置及其他无关ZIP/XML部件按原始字节复制。
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
    MOTOR_CATEGORIES,
    scope_hint,
    visible_fields,
)
from equipeffi.infrastructure.excel.template_resource import (  # noqa: E402
    V62_TEMPLATE_ENTRY,
    V62_TEMPLATE_IDENTITY,
    identity_defined_names,
)
from build_v61_transformer_template import (  # noqa: E402
    FIRST_DATA_ROW,
    HEADER_ROW,
    LAST_DATA_ROW,
    MAIN_NS,
    _cell_map,
    _parse_xml,
    _sheet_table_target,
    _sheet_target,
    _set_inline,
    _tag,
    _xml_bytes,
)


DEFAULT_SOURCE = ROOT / "src" / "equipeffi" / "resources" / "templates" / V62_TEMPLATE_IDENTITY["filename"]
DEFAULT_OUTPUT_NAME = "设备能效分析空白模板_重构版V6_3.xlsx"
DEFAULT_OUTPUT = ROOT / "src" / "equipeffi" / "resources" / "templates" / DEFAULT_OUTPUT_NAME
MANIFEST_PATH = ROOT / "src" / "equipeffi" / "resources" / "TEMPLATE_MANIFEST.json"
V63_TEMPLATE_ID = "equipeffi.device-efficiency.V6.3"
V63_TEMPLATE_VERSION = "V6.3"
MOTOR_SHEET = "电动机"
INSTRUCTIONS_SHEET = "注意事项"
TEMPLATE_NOTES_SHEET = "模板说明"
MOTOR_CATEGORY_NAME = "EV_MOTOR_V63_CATEGORY"
MOTOR_CATEGORY_IDS_NAME = "EV_MOTOR_V63_CATEGORY_IDS"
RETIRED_BASIS_NAME = "EV_MOTOR_V62_BASIS"

EXCEL_VALIDATIONS = {
    "rated_voltage_v": {
        "column": "G", "type": "decimal", "operator": "greaterThanOrEqual",
        "formula1": "0", "error_title": "额定电压",
        "error": "额定电压请按V填写非负数值。",
        "prompt_title": "额定电压", "prompt": "按铭牌电压的V数值填写。",
    },
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
        "error_title": "极数", "error": "极数应填写正偶数。",
        "prompt_title": "极数",
        "prompt": "填写任意正偶数；标准未覆盖值由软件判为不在范围，表6仅留痕。",
    },
    "rated_efficiency_pct": {
        "column": "M", "type": "decimal", "operator": "between",
        "formula1": "1", "formula2": "100", "error_title": "额定效率",
        "error": "请输入1至100之间的百分数点值，例如85.9；不要输入0.859或百分比格式。",
        "prompt_title": "额定效率",
        "prompt": "按电动机铭牌额定效率填写百分数点值，保留小数。",
    },
}


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


def _domain_fields() -> tuple[dict[str, Any], dict[str, list[str]]]:
    descriptors: dict[str, Any] = {}
    required: dict[str, list[str]] = {}
    for category in MOTOR_CATEGORIES:
        category_id = _category_id(category)
        for descriptor in visible_fields(category_id):
            descriptors.setdefault(descriptor.field_id, descriptor)
            if descriptor.required:
                required.setdefault(descriptor.field_id, []).append(category_id)
    return descriptors, required


def _motor_manifest_contract() -> dict[str, Any]:
    categories = tuple(MOTOR_CATEGORIES)
    category_ids = tuple(_category_id(item) for item in categories)
    descriptors, required = _domain_fields()
    fields = deepcopy(next(
        sheet for sheet in V62_TEMPLATE_ENTRY["sheets"]
        if sheet.get("sheet_id") == "motor")["fields"])
    old_to_new = {
        "rated_voltage_kv": "rated_voltage_v",
        "measured_efficiency_pct": "rated_efficiency_pct",
    }
    for field in fields:
        column = str(field.get("column", ""))
        if column == "I":
            field.clear()
            field.update({
                "column": "I", "role": "reserved",
                "label": "历史字段（已停用）",
                "retired_field_id": "efficiency_basis_status",
                "required_for_categories": [],
                "locked": True,
                "hidden": True,
            })
            continue
        field_id = str(field.get("field_id") or "")
        field_id = old_to_new.get(field_id, field_id)
        if field_id in descriptors:
            descriptor = descriptors[field_id]
            field["field_id"] = field_id
            field["label"] = descriptor.label
            field["required_for_categories"] = required.get(field_id, [])
            field.pop("unit", None)
            if descriptor.unit:
                field["unit"] = descriptor.unit
            if field_id in EXCEL_VALIDATIONS:
                field["excel_validation"] = dict(EXCEL_VALIDATIONS[field_id])
            else:
                field.pop("excel_validation", None)
        if column == "F":
            field["category_enum"] = MOTOR_CATEGORY_NAME
    return {
        "sheet_id": "motor", "sheet_name": MOTOR_SHEET,
        "contract_revision": "motor-input.v3", "status": "CONNECTED",
        "header_row": 3,
        "table": {"name": "TblMotor", "ref": "A3:T103"},
        "fields": fields,
        "categories": [
            {"category_id": _category_id(item), "label": _category_label(item),
             "table_no": _field(item, "table_no")}
            for item in categories
        ],
        "category_ids": list(category_ids),
    }


def _identity_names(entry: dict[str, Any]) -> set[str]:
    return set(identity_defined_names(entry))


def _entry(source_hash: str, source_size: int) -> dict[str, Any]:
    entry = deepcopy(V62_TEMPLATE_ENTRY)
    entry.update({
        "template_id": V63_TEMPLATE_ID,
        "template_version": V63_TEMPLATE_VERSION,
        "template_kind": "unified-multi-device-blank-template",
        "template_contract_revision": "unified-v6.v3",
        "status": "CANDIDATE",
        "input_compatibility": "ACCEPTED",
        "legacy_import_compatibility": False,
        "filename": DEFAULT_OUTPUT_NAME,
        "asset_sha256": "",
        "asset_size_bytes": 0,
        "source_filename": V62_TEMPLATE_IDENTITY["filename"],
        "source_sha256": source_hash,
        "source_size_bytes": source_size,
        "source_provenance": (
            "从清单登记的V6.2候选模板派生；仅更新电动机输入契约及其填写说明，"
            "保留离心泵、变压器、共享配置和其他Sheet的原始XML字节。"),
        "generated_by": "tools/build_v63_motor_template.py",
        "authorized_modification": {
            "sheet": "电动机及其专属填写说明",
            "phase": "GB 18613—2020铭牌额定输入接入候选",
            "changes": [
                "电机输入改用铭牌额定效率，额定电压以V填写；不采集实测效率或效率口径选择。",
                "原I列保留位置但隐藏、锁定并清空；V6.3 Reader拒绝非空I列遗留值。",
                "泵、变压器、共享配置和其余设备Sheet保持原始XML字节。",
            ],
        },
        "untouched_sheets": 15,
        "untouched_verification": (
            "tests/unit/test_v63_motor_template.py：泵、变压器、共享配置及其余未修改Sheet"
            "逐项比对ZIP部件字节；V6.2资产SHA保持不变。"),
    })
    for sheet in entry["sheets"]:
        if sheet.get("sheet_id") == "motor":
            sheet.clear()
            sheet.update(_motor_manifest_contract())

    configuration = deepcopy(entry.get("configuration_contract", {}))
    configuration["motor_category_enum"] = {
        "column": "EW", "first_row": 2,
        "defined_name": MOTOR_CATEGORY_NAME,
        "category_ids_column": "EX",
        "category_ids_defined_name": MOTOR_CATEGORY_IDS_NAME,
    }
    # Keep the hidden V6.2 basis labels in 配置 byte-for-byte as historical
    # reference, but do not expose a V6.3 named range or input control for them.
    configuration.pop("motor_efficiency_basis_enum", None)
    configuration["motor_excel_validations"] = {
        field_id: dict(rule) for field_id, rule in EXCEL_VALIDATIONS.items()
    }
    entry["configuration_contract"] = configuration
    entry["motor_capacity_strategy"] = {
        "mechanism": "Excel Table（TblMotor，20列×100条预置数据）+统一Reader",
        "user_action_required": "无：表格内继续填写或粘贴；隐藏I列不参与输入。",
        "business_row_limit": "none",
        "manual_engine_validation": "NOT_RUN；Excel/WPS新增行、保存重开需单独记录。",
    }
    entry["untouched_sheets"] = len(entry["sheets"]) - 3
    return entry


def _locked_cell_style(styles_xml: bytes, motor_xml: bytes) -> tuple[bytes, str]:
    styles = _parse_xml(styles_xml)
    cell_xfs = styles.find(_tag("cellXfs"))
    if cell_xfs is None:
        raise ValueError("模板缺少单元格样式定义")
    motor = _parse_xml(motor_xml)
    cells = {cell.attrib.get("r", ""): cell for cell in motor.findall(
        f".//{_tag('sheetData')}/{_tag('row')}/{_tag('c')}")}
    source = cells.get("I4")
    if source is None:
        raise ValueError("电动机模板缺少I4停用字段样式来源")
    source_style = cell_xfs[int(source.attrib.get("s", "0"))]
    style = deepcopy(source_style)
    protection = style.find(_tag("protection"))
    if protection is None:
        protection = ET.SubElement(style, _tag("protection"))
    protection.set("locked", "1")
    protection.set("hidden", "0")
    style.set("applyProtection", "1")
    index = str(len(cell_xfs))
    cell_xfs.append(style)
    cell_xfs.set("count", str(len(cell_xfs)))
    return _xml_bytes(styles), index


def _validation_by_column(root: ET.Element) -> dict[str, ET.Element]:
    validations = root.find(_tag("dataValidations"))
    if validations is None:
        raise ValueError("电动机Sheet缺少输入数据验证")
    result: dict[str, ET.Element] = {}
    for node in validations.findall(_tag("dataValidation")):
        reference = str(node.attrib.get("sqref", ""))
        match = re.fullmatch(r"([A-Z]+)4:\1(?:[1-9][0-9]*)", reference)
        if match is None:
            raise ValueError(f"电动机数据验证范围无效：{reference}")
        column = match.group(1)
        if column in result:
            raise ValueError(f"电动机{column}列存在重复数据验证")
        result[column] = node
    return result


def _formula(node: ET.Element, child: str) -> str:
    item = node.find(_tag(child))
    return (item.text or "") if item is not None else ""


def _patch_motor_sheet(xml: bytes, locked_style: str) -> bytes:
    root = _parse_xml(xml)
    dimension = root.find(_tag("dimension"))
    if dimension is None or dimension.attrib.get("ref") != "A1:T103":
        raise ValueError("V6.2电动机Sheet维度不符合预期")
    rows = root.find(_tag("sheetData"))
    if rows is None:
        raise ValueError("电动机Sheet缺少sheetData")
    by_row = {int(row.attrib["r"]): row for row in rows.findall(_tag("row"))
              if row.attrib.get("r", "").isdigit()}
    header = by_row.get(HEADER_ROW)
    if header is None:
        raise ValueError("电动机Sheet缺少第3行表头")
    header_cells = _cell_map(header)
    _set_inline(header_cells["G"], "额定电压\n(V)")
    _set_inline(header_cells["I"], "历史字段（已停用）")
    _set_inline(header_cells["M"], "额定效率\n(%)")
    _set_inline(header_cells["S"], "备注")

    for row_number in range(FIRST_DATA_ROW, LAST_DATA_ROW + 1):
        row = by_row.get(row_number)
        if row is None:
            raise ValueError(f"电动机Sheet缺少预置数据行：{row_number}")
        cells = _cell_map(row)
        retired = cells.get("I")
        if retired is None:
            retired = ET.Element(_tag("c"), {"r": f"I{row_number}"})
            row.append(retired)
        for child in list(retired):
            retired.remove(child)
        retired.attrib.pop("t", None)
        retired.set("s", locked_style)

    cols = root.find(_tag("cols"))
    if cols is None:
        raise ValueError("电动机Sheet缺少列宽定义")
    retired_column = [node for node in cols.findall(_tag("col"))
                      if int(node.attrib.get("min", "0")) <= 9
                      <= int(node.attrib.get("max", "0"))]
    if len(retired_column) != 1 or (
            retired_column[0].attrib.get("min") != "9"
            or retired_column[0].attrib.get("max") != "9"):
        raise ValueError("V6.2电动机I列布局不是独立列，拒绝隐式改变相邻列")
    retired_column[0].set("hidden", "1")
    retired_column[0].set("width", "0")
    retired_column[0].set("customWidth", "1")

    validations = root.find(_tag("dataValidations"))
    by_column = _validation_by_column(root)
    if set(by_column) != {"D", "F", "G", "H", "I", "J", "K", "L", "M"}:
        raise ValueError("V6.2电动机输入校验列与既有契约不一致")
    validations.remove(by_column["I"])
    by_column["F"].find(_tag("formula1")).text = MOTOR_CATEGORY_NAME
    g = by_column["G"]
    g.attrib["error"] = "额定电压请按V填写非负数值。"
    g.attrib["prompt"] = "按铭牌电压的V数值填写。"
    m = by_column["M"]
    m.attrib["errorTitle"] = "额定效率"
    m.attrib["error"] = EXCEL_VALIDATIONS["rated_efficiency_pct"]["error"]
    m.attrib["promptTitle"] = "额定效率"
    m.attrib["prompt"] = EXCEL_VALIDATIONS["rated_efficiency_pct"]["prompt"]
    validations.set("count", str(len(validations.findall(_tag("dataValidation")))))
    return _xml_bytes(root)


def _patch_motor_table(xml: bytes) -> bytes:
    root = _parse_xml(xml)
    if root.attrib.get("ref") != "A3:T103":
        raise ValueError("TblMotor范围不符合V6.2契约")
    columns = root.find(_tag("tableColumns"))
    if columns is None:
        raise ValueError("TblMotor缺少tableColumns")
    table_columns = list(columns.findall(_tag("tableColumn")))
    if len(table_columns) != 20:
        raise ValueError(f"TblMotor原始列数不是20：{len(table_columns)}")
    for index, name in ((6, "额定电压\n(V)"),
                        (8, "历史字段（已停用）"),
                        (12, "额定效率\n(%)"),
                        (18, "备注")):
        table_columns[index].set("name", name)
        formula = table_columns[index].find(_tag("calculatedColumnFormula"))
        if formula is not None:
            raise ValueError(f"TblMotor第{index + 1}列仍含有计算列公式")
    return _xml_bytes(root)


def _patch_workbook(xml: bytes, entry: dict[str, Any]) -> bytes:
    root = _parse_xml(xml)
    defined = root.find(_tag("definedNames"))
    if defined is None:
        raise ValueError("工作簿缺少definedNames")
    old_identity = _identity_names(V62_TEMPLATE_ENTRY)
    for node in list(defined.findall(_tag("definedName"))):
        name = node.attrib.get("name", "")
        if (name in old_identity or name in {
                "EV_MOTOR_V62_CATEGORY", "EV_MOTOR_V62_CATEGORY_IDS",
                "EV_MOTOR_V62_BASIS", MOTOR_CATEGORY_NAME,
                MOTOR_CATEGORY_IDS_NAME, RETIRED_BASIS_NAME}):
            defined.remove(node)
    names = {
        MOTOR_CATEGORY_NAME: "'配置'!$EW$2:$EW$9",
        MOTOR_CATEGORY_IDS_NAME: "'配置'!$EX$2:$EX$9",
    }
    for name, expression in names.items():
        ET.SubElement(defined, _tag("definedName"), {"name": name}).text = expression
    for name, value in identity_defined_names(entry).items():
        ET.SubElement(defined, _tag("definedName"), {"name": name}).text = (
            '"' + value.replace('"', '""') + '"')
    return _xml_bytes(root)


def _motor_guidance_text() -> tuple[str, str]:
    category_text = "；".join(
        f"{_category_label(category)}：{scope_hint(_category_id(category))}"
        for category in MOTOR_CATEGORIES
        if _field(category, "table_no") is not None)
    detail = (
        "电动机仅接入GB 18613—2020六类；类别按实际结构明确选择，不从型号或备注推断。"
        "额定功率统一按kW填写，额定电压按V填写，频率按Hz填写；额定效率填铭牌给出的百分数点值1～100，"
        "例如85.9，不输入0.859或百分比格式。10 W填0.010 kW，750 W填0.750 kW。"
        "表1—4按适用条件填写电压、50 Hz和极数，表5按极数选列，表6按铭牌标称最高转速选列；"
        "非适用字段可留空或填0留痕，不以其范围选表。历史I列已停用，不填效率口径。\n"
        + category_text)
    summary = ("GB 18613—2020仅接通以下六类：" + category_text
               + " 额定效率按电动机铭牌额定值填报；额定电压单位为V。")
    return detail, summary


def _patch_guidance(xml: bytes, *, template_notes: bool) -> bytes:
    root = _parse_xml(xml)
    if template_notes:
        note = root.find(f".//{_tag('c')}[@r='B21']")
        if note is None:
            raise ValueError("模板说明Sheet缺少B21电动机输入说明")
        detail, _summary = _motor_guidance_text()
        _set_inline(note, detail)
    else:
        note = root.find(f".//{_tag('c')}[@r='H14']")
        if note is None:
            raise ValueError("注意事项Sheet缺少H14电动机范围摘要")
        _detail, summary = _motor_guidance_text()
        _set_inline(note, summary)
    return _xml_bytes(root)


def _patch_archive(source: Path, output: Path) -> dict[str, Any]:
    with ZipFile(source) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
        motor_path = _sheet_target(archive, MOTOR_SHEET)
        instructions_path = _sheet_target(archive, INSTRUCTIONS_SHEET)
        notes_path = _sheet_target(archive, TEMPLATE_NOTES_SHEET)
        table_path = _sheet_table_target(archive, motor_path, "TblMotor")
        source_motor = archive.read(motor_path)
        source_styles = archive.read("xl/styles.xml")
        source_workbook = archive.read("xl/workbook.xml")
        source_table = archive.read(table_path)
        source_instructions = archive.read(instructions_path)
        source_notes = archive.read(notes_path)

    source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
    entry = _entry(source_hash, source.stat().st_size)
    styles_xml, locked_style = _locked_cell_style(source_styles, source_motor)
    replacements = {
        motor_path: _patch_motor_sheet(source_motor, locked_style),
        "xl/styles.xml": styles_xml,
        "xl/workbook.xml": _patch_workbook(source_workbook, entry),
        table_path: _patch_motor_table(source_table),
        instructions_path: _patch_guidance(source_instructions, template_notes=False),
        notes_path: _patch_guidance(source_notes, template_notes=True),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for info, data in entries:
            archive.writestr(info, replacements.get(info.filename, data))
    return entry


def _update_manifest(entry: dict[str, Any], output: Path) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = deepcopy(entry)
    entry["asset_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    entry["asset_size_bytes"] = output.stat().st_size
    previous = next((index for index, item in enumerate(manifest["templates"])
                     if item.get("template_version") == V63_TEMPLATE_VERSION), None)
    if previous is None:
        source_index = next(index for index, item in enumerate(manifest["templates"])
                            if item.get("template_version") == "V6.2")
        manifest["templates"].insert(source_index + 1, entry)
    else:
        manifest["templates"][previous] = entry
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT,
          *, update_manifest: bool = True) -> tuple[str, int]:
    source, output = Path(source), Path(output)
    if not source.is_file():
        raise SystemExit(f"找不到登记的V6.2模板：{source}")
    expected = str(V62_TEMPLATE_ENTRY["asset_sha256"]).upper()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
    if source_hash != expected:
        raise SystemExit(
            "V6.3派生源不是清单登记的V6.2资产；拒绝生成。\n"
            f"期望 {expected}\n实际 {source_hash}")
    if source.resolve() == output.resolve():
        raise SystemExit("V6.3输出不得覆盖V6.2输入模板")
    entry = _patch_archive(source, output)
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    output_size = output.stat().st_size
    if update_manifest:
        _update_manifest(entry, output)
    return output_hash, output_size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-update-manifest", action="store_true")
    args = parser.parse_args(argv)
    digest, size = build(args.source, args.output,
                         update_manifest=not args.no_update_manifest)
    print(f"V6.3模板: {args.output}")
    print(f"SHA-256: {digest}")
    print(f"大小: {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
