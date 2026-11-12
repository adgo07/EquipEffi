"""V6.5只读ZIP派生V6.6；只改空压机及其配置和身份。"""
from tools.build_v61_transformer_template import _parse_xml, _xml_bytes, _set_inline, _tag, _sheet_target, _sheet_table_target
from equipeffi.infrastructure.excel.template_resource import V65_TEMPLATE_ENTRY, identity_defined_names
from equipeffi.domain.devices.compressor.input_contract import CONTRACT, REVISION
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import re
import sys
from zipfile import ZipFile
from xml.etree import ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
MANIFEST = ROOT / "src/equipeffi/resources/TEMPLATE_MANIFEST.json"
FILENAME = "设备能效分析空白模板_重构版V6_6.xlsx"
CATEGORY_NAME = "EV_COMPRESSOR_V66_CATEGORY"
CATEGORY_IDS = "EV_COMPRESSOR_V66_CATEGORY_IDS"
COOLING_NAME = "EV_COMPRESSOR_V66_COOLING"
COLUMNS = (
    ("A", "序号", "", None, "convenience"), ("B", "名称", "",
                                           "device_name", "input"), ("C", "型号", "", "model", "input"),
    ("D", "数量", "台", "quantity", "input"), ("E", "位置", "",
                                            "location", "input"), ("F", "类别", "", "category_id", "input"),
    ("G", "额定功率（按类别）", "kW", "rated_power_by_category",
     "input"), ("H", "容积流量", "m³/min", "volume_flow_m3_min", "input"),
    ("I", "额定排气压力（表压）", "MPa", "rated_discharge_pressure_mpa",
     "input"), ("J", "冷却方式", "", "cooling_method", "input"),
    ("K", "有效比功率", "kW/(m³/min)", "specific_power_kw_per_m3_min", "input"),
    ("L", "1级限值", "kW/(m³/min)", "grade_1", "result"), ("M",
                                                        "2级限值", "kW/(m³/min)", "grade_2", "result"),
    ("N", "3级限值", "kW/(m³/min)", "grade_3",
     "result"), ("O", "等级", "", "conclusion", "result"),
    ("P", "铭牌照片", "", "photo", "input"), ("Q", "填表备注", "", "user_note", "input"), ("R", "自动备注", "", "messages", "result"))


def build():
    source = MANIFEST.parent / "templates" / V65_TEMPLATE_ENTRY["filename"]
    output = source.with_name(FILENAME)
    if sha256(source.read_bytes()).hexdigest().upper(
    ) != V65_TEMPLATE_ENTRY["asset_sha256"].upper():
        raise ValueError("V6.5源身份不一致")
    entry = deepcopy(V65_TEMPLATE_ENTRY)
    entry.update(template_id="equipeffi.device-efficiency.V6.6", template_version="V6.6", template_contract_revision="unified-v6.v6",
                 filename=FILENAME, source_filename=source.name, source_sha256=sha256(
                     source.read_bytes()).hexdigest().upper(),
                 source_size_bytes=source.stat(
                 ).st_size, generated_by="tools/build_v66_compressor_template.py",
                 source_provenance="Owner批准从V6.5只读派生；只修改空压机及专属配置、身份。",
                 authorized_modification={"sheet": "空压机及专属配置、身份", "phase": "GB19153候选接入", "changes": ["18列输入输出同核契约", "退出业务公式"]})
    sheet = next(s for s in entry["sheets"] if s["sheet_id"] == "compressor")
    sheet.update(status="CONNECTED", contract_revision=REVISION, header_row=3, first_data_row=4,
                 category_ids=[c.category_id for c in CONTRACT.categories], categories=[dict(category_id=c.category_id, label=c.label, table_no=c.table_no) for c in CONTRACT.categories], fields=[])
    for col, label, unit, key, role in COLUMNS:
        f = dict(column=col, label=label, unit=unit, role=role)
        if role == "result":
            f["threshold_key" if key.startswith(
                "grade_") else "result_key"] = key
        elif key:
            f["field_id"] = key
        if col == "G":
            f["category_field_ids"] = {c.category_id: "rated_input_power_kw" if c.table_no and c.table_no >=
                                       5 else "rated_motor_output_power_kw" for c in CONTRACT.categories if c.table_no}
        sheet["fields"].append(f)
    entry["configuration_contract"]["compressor_enum"] = {"category_name": CATEGORY_NAME, "category_ids_name": CATEGORY_IDS,
                                                          "cooling_name": COOLING_NAME, "label_column": "FG", "id_column": "FH", "required_column": "FI", "power_column": "FJ"}
    entry["compressor_capacity_strategy"] = {
        "first_row": 4,
        "last_row": 1048576,
        "user_action_required": "无；继续填写或粘贴。"}
    with ZipFile(source) as z:
        parts = [(info, z.read(info.filename)) for info in z.infolist()]
        part = _sheet_target(z, "空压机")
        config_part = _sheet_target(z, "配置")
        try:
            table_part = _sheet_table_target(z, part, "TblCompressor")
        except (ValueError, KeyError):
            table_part = None
    data = {i.filename: b for i, b in parts}
    root = _parse_xml(data[part])
    for col, label, unit, key, role in COLUMNS:
        cell = root.find(f".//{_tag('c')}[@r='{col}3']")
        if cell is None:
            raise ValueError("空压机表头缺失")
        _set_inline(cell, label + (f"\n({unit})" if unit else ""))
    for row in root.find(_tag("sheetData")):
        if int(row.get("r")) < 4:
            continue
        for cell in row:
            col = re.match(r"[A-Z]+", cell.get("r")).group()
            if col in {"L", "M", "N", "O", "R"}:
                for child in list(cell):
                    cell.remove(child)
                cell.attrib.pop("t", None)
    old = root.find(_tag("dataValidations"))
    if old is not None:
        root.remove(old)
    validations = ET.Element(_tag("dataValidations"), count="8")
    rules = [("D", "whole", "greaterThan", "0"), ("F", "list", "", CATEGORY_NAME), ("G", "decimal", "greaterThan", "0"),
             ("H", "decimal", "greaterThan", "0"), ("I", "decimal", "greaterThan", "0"), ("J", "list", "", COOLING_NAME), ("K", "decimal", "greaterThan", "0")]
    validations.set("count", str(len(rules)))
    for col, kind, op, formula in rules:
        attrs = dict(
            type=kind,
            sqref=f"{col}4:{col}1048576",
            allowBlank="1",
            showErrorMessage="1",
            showInputMessage="1",
            errorTitle="输入有误",
            error="请按字段单位填写有效数据。")
        if op:
            attrs["operator"] = op
        if col == "G":
            attrs["prompt"] = "表1/2填主驱动电动机额定输出功率合计；表3/4填额定输出功率；直联便携式填机组额定输入功率。"
        if col == "K":
            attrs["prompt"] = "填有效机组比功率；变转速类别填有效综合比功率。"
        node = ET.SubElement(validations, _tag("dataValidation"), attrs)
        ET.SubElement(node, _tag("formula1")).text = formula
    # dataValidations须位于pageMargins前，保留OOXML子元素顺序。
    siblings = list(root)
    pos = next(
        (i for i,
         n in enumerate(siblings) if n.tag in {
             _tag("pageMargins"),
             _tag("pageSetup"),
             _tag("drawing"),
             _tag("tableParts")}),
        len(siblings))
    root.insert(pos, validations)
    config = _parse_xml(data[config_part])
    rows = config.find(_tag("sheetData"))
    byrow = {int(n.get("r")): n for n in rows}

    def put(row, col, text):
        target = byrow.get(row)
        if target is None:
            target = ET.SubElement(rows, _tag("row"), r=str(row))
            byrow[row] = target
        address = f"{col}{row}"
        cell = next((n for n in target if n.get("r") == address), None)
        if cell is None:
            cell = ET.SubElement(target, _tag("c"), r=address)
        _set_inline(cell, text)
    for col, text in (("FG", "空压机类别"), ("FH", "空压机类别ID"),
                      ("FI", "空压机必填字段"), ("FJ", "空压机功率字段"), ("FK", "空压机冷却")):
        put(1, col, text)
    for n, c in enumerate(CONTRACT.categories, 2):
        put(n, "FG", c.label)
        put(n, "FH", c.category_id)
        put(n, "FI", ",".join(f.field_id for f in CONTRACT.visible_fields(
            c.category_id) if f.required))
        put(n, "FJ", next((f.field_id for f in CONTRACT.visible_fields(
            c.category_id) if f.unit == "kW"), ""))
    for n, text in enumerate(("风冷", "液冷"), 2):
        put(n, "FK", text)
    workbook = _parse_xml(data["xl/workbook.xml"])
    names = workbook.find(_tag("definedNames"))
    old_names = set(identity_defined_names(V65_TEMPLATE_ENTRY))
    for node in list(names):
        if node.get("name") in old_names or node.get(
                "name", "").startswith("EV_COMPRESSOR_V66_"):
            names.remove(node)
    for name, col, count in ((CATEGORY_NAME, "FG", len(CONTRACT.categories)), (
            CATEGORY_IDS, "FH", len(CONTRACT.categories)), (COOLING_NAME, "FK", 2)):
        ET.SubElement(
            names,
            _tag("definedName"),
            name=name).text = f"'配置'!${col}$2:${col}${
            count + 1}"
    for name, value in identity_defined_names(entry).items():
        ET.SubElement(
            names,
            _tag("definedName"),
            name=name).text = f'"{value}"'
    replacements = {
        part: _xml_bytes(root),
        config_part: _xml_bytes(config),
        "xl/workbook.xml": _xml_bytes(workbook)}
    if table_part:
        table = _parse_xml(data[table_part])
        for node, (_, label, unit, _, _) in zip(
                table.find(_tag("tableColumns")), COLUMNS):
            node.set("name", label + (f"\n({unit})" if unit else ""))
            for child in list(node):
                if child.tag in {_tag("calculatedColumnFormula"), _tag(
                        "totalsRowFormula")}:
                    node.remove(child)
        replacements[table_part] = _xml_bytes(table)
    with ZipFile(output, "w") as z:
        for info, raw in parts:
            z.writestr(info, replacements.get(info.filename, raw))
    entry.update(
        asset_sha256=sha256(
            output.read_bytes()).hexdigest().upper(),
        asset_size_bytes=output.stat().st_size)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["templates"] = [e for e in manifest["templates"]
                             if e["template_version"] != "V6.6"] + [entry]
    MANIFEST.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2) + "\n",
        encoding="utf-8",
        newline="\n")
    print(output.name, entry["asset_sha256"])


if __name__ == "__main__":
    build()
