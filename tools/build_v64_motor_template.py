"""Derive V6.4 from pinned V6.3 by patching only motor-owned XML."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from equipeffi.domain.devices.motor_hv.input_contract import MOTOR_PRODUCT_INPUT_CONTRACT as CONTRACT, COOLING_CODES, HV_CATEGORY_ID
from equipeffi.infrastructure.excel.template_resource import V63_TEMPLATE_ENTRY, identity_defined_names
from build_v61_transformer_template import _sheet_target, _sheet_table_target, _parse_xml, _tag, _xml_bytes, _set_inline

MANIFEST = ROOT / "src/equipeffi/resources/TEMPLATE_MANIFEST.json"
FILENAME = "设备能效分析空白模板_重构版V6_4.xlsx"


def build():
    source = ROOT / "src/equipeffi/resources/templates" / V63_TEMPLATE_ENTRY["filename"]
    output = source.with_name(FILENAME)
    if hashlib.sha256(source.read_bytes()).hexdigest().upper() != V63_TEMPLATE_ENTRY["asset_sha256"].upper():
        raise ValueError("V6.3派生源身份不匹配")
    entry = deepcopy(V63_TEMPLATE_ENTRY)
    entry.update(template_id="equipeffi.device-efficiency.V6.4", template_version="V6.4",
        template_contract_revision="unified-v6.v4", filename=FILENAME,
        source_filename=source.name, source_sha256=V63_TEMPLATE_ENTRY["asset_sha256"],
        source_size_bytes=source.stat().st_size, generated_by="tools/build_v64_motor_template.py",
        source_provenance="从登记V6.3定点派生；仅修改电动机及其专属配置、说明与身份。",
        authorized_modification={"sheet": "电动机及专属配置、说明", "phase": "GB30254候选产品接入",
            "changes": ["F明确标准类别；I高压冷却IC代码；其他设备Sheet和配置内容保持"]})
    entry["untouched_sheets"] = len(entry["sheets"]) - 4
    entry["untouched_verification"] = "tests/test_motor_hv_excel.py逐部件验证；旧模板字节不变"
    entry.pop("capacity_measurements", None)
    motor = next(s for s in entry["sheets"] if s["sheet_id"] == "motor")
    motor["contract_revision"] = "motor-input.v4"
    motor["categories"] = [dict(category_id=c.category_id, label=c.label, table_no=c.table_no) for c in CONTRACT.categories]
    motor["category_ids"] = [c.category_id for c in CONTRACT.categories]
    descriptors = {f.field_id: f for c in CONTRACT.categories for f in CONTRACT.visible_fields(c.category_id)}
    for f in motor["fields"]:
        if f["column"] == "I":
            f.clear(); f.update(column="I", role="input", field_id="cooling_method", label="冷却方式（仅高压）",
                locked=False, hidden=False, required_for_categories=[HV_CATEGORY_ID],
                excel_validation={"column": "I", "type": "list", "formula1": "EV_MOTOR_V64_COOLING"})
        elif f["column"] == "F":
            f["category_enum"] = "EV_MOTOR_V64_CATEGORY"
        field = f.get("field_id")
        if field in descriptors:
            f["required_for_categories"] = [c.category_id for c in CONTRACT.categories
                if any(v.field_id == field and v.required for v in CONTRACT.visible_fields(c.category_id))]
    config = entry["configuration_contract"]
    config["motor_category_enum"].update(defined_name="EV_MOTOR_V64_CATEGORY", category_ids_defined_name="EV_MOTOR_V64_CATEGORY_IDS")
    config["motor_cooling_enum"] = dict(column="FA", first_row=2, defined_name="EV_MOTOR_V64_COOLING", values=list(COOLING_CODES))
    config["motor_excel_validations"]["cooling_method"] = dict(column="I", type="list", formula1="EV_MOTOR_V64_COOLING")
    config["motor_excel_validations"]["rated_frequency_hz"]["prompt"] = "数字或原始频率范围；GB18613表1—4核对50 Hz，表5/6留痕；GB30254高压必填且仅50 Hz适用。"
    config["motor_excel_validations"]["poles"]["prompt"] = "填写正偶数；GB18613表6仅留痕；GB30254高压必填，无对应极数列按不在范围处理。"
    for field in motor["fields"]:
        if field.get("field_id") in config["motor_excel_validations"]:
            field["excel_validation"] = deepcopy(config["motor_excel_validations"][field["field_id"]])
    entry["motor_capacity_strategy"]["user_action_required"] = "无：表格内继续填写或粘贴；I列仅高压填IC代码。"
    with ZipFile(source) as z:
        parts = [(info, z.read(info.filename)) for info in z.infolist()]
        motor_path = _sheet_target(z, "电动机")
        config_path = _sheet_target(z, "配置")
        table_path = _sheet_table_target(z, motor_path, "TblMotor")
        notes_paths = [(_sheet_target(z, "模板说明"), "B21"), (_sheet_target(z, "注意事项"), "H14")]
    data = {info.filename: raw for info, raw in parts}
    replacements = {}
    root = _parse_xml(data[motor_path])
    cells = {c.attrib["r"]: c for c in root.findall(f".//{_tag('c')}")}
    _set_inline(cells["I3"], "冷却方式（仅高压）")
    for n in range(4,104):
        cells[f"I{n}"].set("s", cells[f"J{n}"].get("s", "0"))
    for col in root.findall(f"{_tag('cols')}/{_tag('col')}"):
        if col.get("min") == "9" and col.get("max") == "9":
            col.set("hidden", "0"); col.set("width", "22")
    validations = root.find(_tag("dataValidations"))
    for node in validations:
        if node.get("sqref", "").startswith("F4:"):
            node.find(_tag("formula1")).text = "EV_MOTOR_V64_CATEGORY"
        for rule in config["motor_excel_validations"].values():
            if node.get("sqref", "").startswith(rule["column"] + "4:") and "prompt" in rule:
                node.set("prompt", rule["prompt"])
    node = ET.SubElement(validations, _tag("dataValidation"), dict(type="list", allowBlank="1",
        showErrorMessage="1", errorTitle="冷却方式", error="请从列表选择冷却IC代码。", sqref="I4:I1048576"))
    ET.SubElement(node, _tag("formula1")).text = "EV_MOTOR_V64_COOLING"
    validations.set("count", str(len(validations)))
    replacements[motor_path] = _xml_bytes(root)
    table = _parse_xml(data[table_path]); table.find(_tag("tableColumns"))[8].set("name", "冷却方式（仅高压）")
    replacements[table_path] = _xml_bytes(table)
    config_root = _parse_xml(data[config_path]); rows = config_root.find(_tag("sheetData"))
    by_row = {int(r.get("r")): r for r in rows}
    def put(row_no, col, value):
        row = by_row.get(row_no)
        if row is None:
            row = ET.SubElement(rows, _tag("row"), {"r": str(row_no)}); by_row[row_no] = row
        cell = next((c for c in row if c.get("r") == f"{col}{row_no}"), None)
        if cell is None: cell = ET.SubElement(row, _tag("c"), {"r": f"{col}{row_no}"})
        _set_inline(cell, value)
    for n, category in enumerate(CONTRACT.categories, 2):
        put(n, "EW", category.label); put(n, "EX", category.category_id)
    for n, code in enumerate(COOLING_CODES, 2): put(n, "FA", code)
    # Cells must remain in ascending column order for native spreadsheet engines.
    def column_number(cell):
        value = 0
        for char in ''.join(c for c in cell.get('r','') if c.isalpha()): value = value * 26 + ord(char) - 64
        return value
    for row in rows: row[:] = sorted(row, key=column_number)
    replacements[config_path] = _xml_bytes(config_root)
    workbook = _parse_xml(data["xl/workbook.xml"]); defined = workbook.find(_tag("definedNames"))
    identities = set(identity_defined_names(V63_TEMPLATE_ENTRY))
    for node in list(defined):
        if node.get("name") in identities or node.get("name", "").startswith("EV_MOTOR_V63_"):
            defined.remove(node)
    names = {"EV_MOTOR_V64_CATEGORY": "'配置'!$EW$2:$EW$10", "EV_MOTOR_V64_CATEGORY_IDS": "'配置'!$EX$2:$EX$10",
        "EV_MOTOR_V64_COOLING": "'配置'!$FA$2:$FA$11"}
    for name, expr in names.items(): ET.SubElement(defined, _tag("definedName"), {"name": name}).text = expr
    for name, value in identity_defined_names(entry).items():
        ET.SubElement(defined, _tag("definedName"), {"name": name}).text = '"' + value + '"'
    replacements["xl/workbook.xml"] = _xml_bytes(workbook)
    guidance = "\nGB 30254—2024高压三相笼型异步电动机候选已实现，待验收；在F明确选择高压类别，G按V填3000/3300/6000/10000，H填50 Hz，I必填冷却IC代码，J功率kW，K极数，L留空，M额定效率1～100百分数点值；非50Hz或文本范围按不在范围处理。低压类别I留空；软件不测量或核验试验报告。"
    for path, address in notes_paths:
        root = _parse_xml(data[path]); cell = root.find(f".//{_tag('c')}[@r='{address}']")
        text = ''.join(t.text or '' for t in cell.iter(_tag('t')))
        text = text.replace("电动机仅接入GB 18613—2020六类", "低压类别接入GB 18613—2020六类").replace("历史I列已停用，不填效率口径。", "I列仅高压填写冷却IC代码。")
        _set_inline(cell, text + guidance); replacements[path] = _xml_bytes(root)
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        for info, raw in parts: z.writestr(info, replacements.get(info.filename, raw))
    entry["asset_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    entry["asset_size_bytes"] = output.stat().st_size
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["templates"] = [e for e in manifest["templates"] if e["template_version"] != "V6.4"] + [entry]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(dict(path=str(output), sha256=entry["asset_sha256"]),ensure_ascii=False))


if __name__ == "__main__":
    build()
