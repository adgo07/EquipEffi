"""Derive V6.5 from pinned V6.4, patching only motor-owned workbook parts."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from equipeffi.domain.devices.motor.product_input_contract import MOTOR_PRODUCT_INPUT_CONTRACT as CONTRACT, MOTOR_V5_REVISION
from equipeffi.domain.devices.motor_hv.input_contract import COOLING_CODES as HV_COOLING, HV_CATEGORY_ID
from equipeffi.domain.devices.motor_pmsm.input_contract import BRANCHES, COOLING_CODES as PMSM_COOLING
from equipeffi.infrastructure.excel.template_resource import V64_TEMPLATE_ENTRY, identity_defined_names
from tools.build_v61_transformer_template import (
    _column_number, _parse_xml, _set_inline, _sheet_table_target, _sheet_target, _tag, _xml_bytes,
)

MANIFEST = ROOT / "src/equipeffi/resources/TEMPLATE_MANIFEST.json"
FILENAME = "设备能效分析空白模板_重构版V6_5.xlsx"
CATEGORY_NAME = "EV_MOTOR_V65_CATEGORY"
CATEGORY_IDS = "EV_MOTOR_V65_CATEGORY_IDS"
COOLING_NAME = "EV_MOTOR_V65_COOLING"
COOLING = list(dict.fromkeys((*HV_COOLING, *PMSM_COOLING)))
SPEED_LABEL = "转速（按类别填写）"
SPEED_HEADER = SPEED_LABEL + "\n(r/min)"
GUIDANCE = (
    "\nGB 30253—2024适用于一般用途或防爆用途、连续工作制的永磁同步电动机。"
    "F列选择低压/高压异步起动、低压/高压变频调速或电梯用。"
    "异步起动填H列额定频率50 Hz及K列极数，L列留空；变频调速及电梯用填L列额定转速，H、K列留空。"
    "I列仅高压类别填写冷却IC代码；低压及电梯用留空。"
    "GB 18613表6的L列仍填铭牌标称最高转速。软件按额定效率评价。"
)


def _entry(source: Path) -> dict:
    entry = deepcopy(V64_TEMPLATE_ENTRY)
    entry.update(template_id="equipeffi.device-efficiency.V6.5", template_version="V6.5",
                 template_contract_revision="unified-v6.v5", filename=FILENAME,
                 source_filename=source.name, source_sha256=V64_TEMPLATE_ENTRY["asset_sha256"],
                 source_size_bytes=source.stat().st_size, generated_by="tools/build_v65_motor_template.py",
                 source_provenance="从登记V6.4派生，修改电动机及专属配置、说明与身份。",
                 untouched_verification="tests/test_motor_pmsm_excel.py逐部件验证；旧模板字节保留",
                 authorized_modification={"sheet": "电动机及专属配置、说明", "phase": "GB30253候选产品接入",
                    "changes": ["F新增五个永磁分支", "I按高压分支填写冷却IC代码", "L按类别填写转速"]})
    motor = next(sheet for sheet in entry["sheets"] if sheet["sheet_id"] == "motor")
    motor["contract_revision"] = MOTOR_V5_REVISION
    motor["categories"] = [dict(category_id=item.category_id, label=item.label, table_no=item.table_no)
                           for item in CONTRACT.categories]
    motor["category_ids"] = [item.category_id for item in CONTRACT.categories]
    fields_by_category = {item.category_id: CONTRACT.visible_fields(item.category_id) for item in CONTRACT.categories}
    speed_fields = {category: "rated_speed_rpm" for category, branch in BRANCHES.items() if not branch.pole_axis}
    config = entry["configuration_contract"]
    config["motor_category_enum"].update(defined_name=CATEGORY_NAME, category_ids_defined_name=CATEGORY_IDS)
    config["motor_cooling_enum"].update(defined_name=COOLING_NAME, values=COOLING)
    config["motor_category_requirements"] = {
        "first_row": 2, "required_fields_column": "FB", "speed_field_column": "FC", "branch_column": "FD",
    }
    rules = config["motor_excel_validations"]
    rules["cooling_method"]["formula1"] = COOLING_NAME
    rules["rated_frequency_hz"]["prompt"] = "永磁和高压笼型异步起动填50 Hz；永磁变频及电梯用留空。GB18613按类别填报。"
    rules["poles"].update(
        formula1='OR(K4="",AND(ISNUMBER(K4),K4>0,MOD(K4,1)=0,OR(MOD(K4,2)=0,LEFT(F4,8)="GB 30253",LEFT(F4,8)="gb30253_")))',
        prompt="永磁异步起动填正整数；其他需要极数的类别填正偶数；永磁变频及电梯用留空。",
        error="极数应为正整数；GB18613及GB30254需填正偶数。")
    rules["max_nameplate_speed_rpm"] = {
        "column": "L", "type": "decimal", "operator": "greaterThanOrEqual", "formula1": "0",
        "prompt": "永磁变频及电梯用填额定转速；GB18613表6填铭牌标称最高转速；其余按类别留空。",
    }
    for field in motor["fields"]:
        column = field["column"]
        field_id = field.get("field_id")
        if column == "F":
            field["category_enum"] = CATEGORY_NAME
        if column == "L":
            field.update(label=SPEED_LABEL, category_field_ids=speed_fields)
        if field_id:
            field["required_for_categories"] = [category for category, descriptors in fields_by_category.items()
                if any(descriptor.field_id == field.get("category_field_ids", {}).get(category, field_id)
                       and descriptor.required for descriptor in descriptors)]
        if field_id in rules:
            field["excel_validation"] = deepcopy(rules[field_id])
    entry["motor_capacity_strategy"]["user_action_required"] = "无。继续填写或粘贴，H、I、K、L列按F的类别填写。"
    return entry


def _update_config(data):
    root = _parse_xml(data)
    rows = root.find(_tag("sheetData"))
    by_row = {int(row.get("r")): row for row in rows}

    def put(number, column, value):
        row = by_row[number]
        address = f"{column}{number}"
        cell = next((item for item in row if item.get("r") == address), None)
        if cell is None:
            cell = ET.SubElement(row, _tag("c"), {"r": address})
        _set_inline(cell, value)

    for column, label in (("FB", "电动机类别必填字段"), ("FC", "L列适用字段"), ("FD", "标准分支")):
        put(1, column, label)
    for number, item in enumerate(CONTRACT.categories, 2):
        category = item.category_id
        fields = CONTRACT.visible_fields(category)
        branch = BRANCHES.get(category)
        put(number, "EW", item.label)
        put(number, "EX", category)
        put(number, "FB", "、".join(f"{field.label}（{field.unit}）" if field.unit else field.label
                                   for field in fields if field.required))
        put(number, "FC", next((field.field_id for field in fields if field.field_id in
                                 {"rated_speed_rpm", "max_nameplate_speed_rpm"}), ""))
        put(number, "FD", branch.code if branch else "GB30254" if category == HV_CATEGORY_ID else
            f"GB18613 表{item.table_no}" if item.table_no is not None else "")
    for number, code in enumerate(COOLING, 2):
        put(number, "FA", code)
    for row in rows:
        row[:] = sorted(row, key=lambda cell: _column_number(re.match(r"[A-Z]+", cell.get("r")).group()))
    return _xml_bytes(root)


def build():
    source = MANIFEST.parent / "templates" / V64_TEMPLATE_ENTRY["filename"]
    output = source.with_name(FILENAME)
    if sha256(source.read_bytes()).hexdigest().upper() != V64_TEMPLATE_ENTRY["asset_sha256"].upper():
        raise ValueError("V6.4派生源身份不匹配")
    entry = _entry(source)
    with ZipFile(source) as archive:
        parts = [(info, archive.read(info.filename)) for info in archive.infolist()]
        motor_path = _sheet_target(archive, "电动机")
        config_path = _sheet_target(archive, "配置")
        table_path = _sheet_table_target(archive, motor_path, "TblMotor")
        notes_paths = [(_sheet_target(archive, "模板说明"), "B21", "190"),
                       (_sheet_target(archive, "注意事项"), "H14", "320")]
    data = {info.filename: raw for info, raw in parts}
    motor = _parse_xml(data[motor_path])
    _set_inline(motor.find(f".//{_tag('c')}[@r='L3']"), SPEED_HEADER)
    rules = {rule["column"]: rule for rule in entry["configuration_contract"]["motor_excel_validations"].values()}
    for node in motor.find(_tag("dataValidations")):
        column = re.match(r"[A-Z]+", node.get("sqref")).group()
        if column == "F":
            node.find(_tag("formula1")).text = CATEGORY_NAME
        for key in ("prompt", "error"):
            if key in rules.get(column, {}):
                node.set(key, rules[column][key])
        if column in {"I", "K"}:
            node.find(_tag("formula1")).text = rules[column]["formula1"]
    table = _parse_xml(data[table_path])
    table.find(_tag("tableColumns"))[11].set("name", SPEED_HEADER)
    workbook = _parse_xml(data["xl/workbook.xml"])
    defined = workbook.find(_tag("definedNames"))
    old_identities = set(identity_defined_names(V64_TEMPLATE_ENTRY))
    for node in list(defined):
        if node.get("name") in old_identities or node.get("name", "").startswith("EV_MOTOR_V64_"):
            defined.remove(node)
    for name, column, count in ((CATEGORY_NAME, "EW", len(CONTRACT.categories)),
                                (CATEGORY_IDS, "EX", len(CONTRACT.categories)),
                                (COOLING_NAME, "FA", len(COOLING))):
        ET.SubElement(defined, _tag("definedName"), name=name).text = f"'配置'!${column}$2:${column}${count + 1}"
    for name, value in identity_defined_names(entry).items():
        ET.SubElement(defined, _tag("definedName"), name=name).text = f'"{value}"'
    replacements = {
        motor_path: _xml_bytes(motor), table_path: _xml_bytes(table),
        config_path: _update_config(data[config_path]), "xl/workbook.xml": _xml_bytes(workbook),
    }
    for path, address, height in notes_paths:
        root = _parse_xml(data[path])
        number = address[1:]
        row = root.find(f".//{_tag('row')}[@r='{number}']")
        cell = row.find(f"{_tag('c')}[@r='{address}']")
        current = "".join(item.text or "" for item in cell.iter(_tag("t")))
        _set_inline(cell, current + GUIDANCE)
        row.attrib.update(ht=height, customHeight="1")
        replacements[path] = _xml_bytes(root)
    with ZipFile(output, "w") as archive:
        for info, raw in parts:
            archive.writestr(info, replacements.get(info.filename, raw))
    entry.update(asset_sha256=sha256(output.read_bytes()).hexdigest().upper(), asset_size_bytes=output.stat().st_size)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["templates"] = [item for item in manifest["templates"] if item["template_version"] != "V6.5"] + [entry]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{output.name} {entry['asset_sha256']}")


if __name__ == "__main__":
    build()
