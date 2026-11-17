"""V6.6只读ZIP派生V6.7；只改工业锅炉及其配置和身份。"""
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
sys.path.insert(0, str(ROOT))
from tools.build_v61_transformer_template import _parse_xml, _xml_bytes, _set_inline, _tag, _sheet_target, _sheet_table_target
from equipeffi.infrastructure.excel.template_resource import V66_TEMPLATE_ENTRY, identity_defined_names
from equipeffi.domain.devices.boiler.input_contract import CONTRACT, REVISION

MANIFEST = ROOT / "src/equipeffi/resources/TEMPLATE_MANIFEST.json"
FILENAME = "设备能效分析空白模板_重构版V6_7.xlsx"
CATEGORY_NAME = "EV_BOILER_V67_CATEGORY"
CATEGORY_IDS = "EV_BOILER_V67_CATEGORY_IDS"
from equipeffi.infrastructure.excel.boiler_sheet_contract import COLUMNS, INPUT_COLUMNS, RESULT_COLUMNS, column_letter



def _capacity_styles(root, styles_data):
    """只追加保护样式，原XF索引与内容不变；列默认覆盖整张表。"""
    styles = _parse_xml(styles_data)
    xfs = styles.find(_tag("cellXfs"))
    variants = {}

    def protection_style(index, locked):
        key = (int(index), locked)
        if key in variants:
            return variants[key]
        cloned = deepcopy(xfs[key[0]])
        node = cloned.find(_tag("protection"))
        if node is None:
            node = ET.SubElement(cloned, _tag("protection"))
        node.set("locked", "1" if locked else "0")
        cloned.set("applyProtection", "1")
        raw = ET.tostring(cloned)
        found = next((n for n, existing in enumerate(xfs) if ET.tostring(existing) == raw), None)
        if found is None:
            found = len(xfs)
            xfs.append(cloned)
        variants[key] = str(found)
        return str(found)

    cols = root.find(_tag("cols"))
    original_cols = list(cols)
    expanded = []
    for old in original_cols:
        first, last = int(old.get("min")), int(old.get("max"))
        for number in range(first, min(last, 19) + 1):
            col = deepcopy(old)
            col.set("min", str(number)); col.set("max", str(number))
            letter = chr(64 + number)
            if letter in INPUT_COLUMNS | RESULT_COLUMNS:
                col.set("style", protection_style(col.get("style", "0"), letter in RESULT_COLUMNS))
            expanded.append(col)
        if last > 19:
            tail = deepcopy(old); tail.set("min", str(max(first, 20)))
            expanded.append(tail)
    cols[:] = expanded
    for row in root.find(_tag("sheetData")):
        number = int(row.get("r"))
        for cell in row:
            letter = re.match(r"[A-Z]+", cell.get("r")).group()
            if number <= 3 or letter in RESULT_COLUMNS:
                cell.set("s", protection_style(cell.get("s", "0"), True))
            elif letter in INPUT_COLUMNS:
                cell.set("s", protection_style(cell.get("s", "0"), False))
    total = root.find(f".//{_tag('c')}[@r='R1']")
    if total is None:
        raise ValueError("工业锅炉数量合计格R1缺失")
    for child in list(total):
        total.remove(child)
    total.attrib.pop("t", None)
    ET.SubElement(total, _tag("f")).text = "SUM(D4:D1048576)"
    xfs.set("count", str(len(xfs)))
    return _xml_bytes(styles)

def build():
    source = MANIFEST.parent / "templates" / V66_TEMPLATE_ENTRY["filename"]
    output = source.with_name(FILENAME)
    if sha256(source.read_bytes()).hexdigest().upper(
    ) != V66_TEMPLATE_ENTRY["asset_sha256"].upper():
        raise ValueError("V6.6源身份不一致")
    entry = deepcopy(V66_TEMPLATE_ENTRY)
    entry.update(template_id="equipeffi.device-efficiency.V6.7", template_version="V6.7", template_contract_revision="unified-v6.v7",
                 filename=FILENAME, source_filename=source.name, source_sha256=sha256(
                     source.read_bytes()).hexdigest().upper(),
                 source_size_bytes=source.stat(
                 ).st_size, generated_by="tools/build_v67_boiler_template.py",
                 source_provenance="Owner批准从V6.6只读派生；只修改工业锅炉及专属配置、身份。",
                 authorized_modification={"sheet": "工业锅炉及专属配置、身份", "phase": "GB24500候选接入", "changes": ["19列输入输出同核契约", "退出业务公式"]})
    sheet = next(s for s in entry["sheets"] if s["sheet_id"] == "industrial_boiler")
    sheet.update(status="CONNECTED", contract_revision=REVISION, header_row=3, first_data_row=4,
                 category_ids=[c.category_id for c in CONTRACT.categories], categories=[dict(category_id=c.category_id, label=c.label, form=c.form, heat=c.heat, basis=c.basis) for c in CONTRACT.categories], fields=[])
    for col, label, unit, key, role in COLUMNS:
        f = dict(column=col, label=label, unit=unit, role=role)
        if role == "result":
            f["threshold_key" if key.startswith(
                "grade_") else "result_key"] = key
        elif key:
            f["field_id"] = key
        sheet["fields"].append(f)
    entry["configuration_contract"]["boiler_enum"] = {"category_name": CATEGORY_NAME, "category_ids_name": CATEGORY_IDS,
                                                          "fuel_names": "EV_BOILER_V67_FUEL_", "label_column": "FL", "id_column": "FM", "required_column": "FN", "capacity_unit_column": "FO"}
    entry["boiler_capacity_strategy"] = {
        "first_row": 4,
        "last_row": 1048576,
        "user_action_required": "无；输入列全列解锁并校验，继续填写或粘贴，无需扩展Table。", "mechanism": "full-column-unlocked-input + full-range-validation + all-row-reader", "quantity_sum": "SUM(D4:D1048576)", "manual_engine_validation": "NOT_RUN"}
    with ZipFile(source) as z:
        parts = [(info, z.read(info.filename)) for info in z.infolist()]
        part = _sheet_target(z, "工业锅炉")
        config_part = _sheet_target(z, "配置")
        try:
            table_part = _sheet_table_target(z, part, "TblBoiler")
        except (ValueError, KeyError):
            table_part = None
    data = {i.filename: b for i, b in parts}
    root = _parse_xml(data[part])
    for col, label, unit, key, role in COLUMNS:
        cell = root.find(f".//{_tag('c')}[@r='{col}3']")
        if cell is None:
            raise ValueError("工业锅炉表头缺失")
        _set_inline(cell, label + (f"\n({unit})" if unit else ""))
    for row in root.find(_tag("sheetData")):
        if int(row.get("r")) < 4:
            continue
        for cell in row:
            col = re.match(r"[A-Z]+", cell.get("r")).group()
            if col in {"M", "N", "O", "P", "S"}:
                for child in list(cell):
                    cell.remove(child)
                cell.attrib.pop("t", None)
    old = root.find(_tag("dataValidations"))
    if old is not None:
        root.remove(old)
    validations = ET.Element(_tag("dataValidations"), count="8")
    rules = [("D", "whole", "greaterThan", "0"), ("F", "list", "", CATEGORY_NAME),
             ("G", "list", "", 'INDIRECT("EV_BOILER_V67_FUEL_"&IFERROR(MATCH(F4,EV_BOILER_V67_CATEGORY,0),23))'),
             ("H", "decimal", "greaterThanOrEqual", "0"), ("I", "decimal", "greaterThanOrEqual", "0"),
             ("J", "decimal", "greaterThan", "0"), ("K", "decimal", "between", "0"),
             ("L", "decimal", "greaterThanOrEqual", "0"), ("O", "decimal", "greaterThan", "0")]
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
        if col == "H":
            attrs["prompt"] = "按F锅炉类别填写数字：蒸汽t/h；热水MW；不作D/Q换算。"
        if col == "L":
            attrs["prompt"] = "唯一被评价热效率；设计值或测试值采用同一比较方法，冷凝低位可大于100。"
        if col == "O":
            attrs["promptTitle"] = "低热值生物质条件输入"
            attrs["prompt"] = "仅生物质J<8374时填该设备设计热效率，必须大于0；其他情况由软件输出。改类别/热值后重新补录，勿沿用旧结果。"
        node = ET.SubElement(validations, _tag("dataValidation"), attrs)
        ET.SubElement(node, _tag("formula1")).text = formula
        if col == "K":
            ET.SubElement(node, _tag("formula2")).text = "100"
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
    for col, text in (("FL", "锅炉类别"), ("FM", "锅炉类别ID"), ("FN", "锅炉必填字段"), ("FO", "锅炉容量单位")):
        put(1, col, text)
    from equipeffi.domain.devices.boiler.input_contract import COALS
    for n, c in enumerate(CONTRACT.categories, 2):
        put(n, "FL", c.label); put(n, "FM", c.category_id)
        put(n, "FN", ",".join(f.field_id for f in CONTRACT.visible_fields(c.category_id) if f.required))
        put(n, "FO", "t/h" if c.form == "steam" else "MW" if c.form == "hot_water" else "")
        # 每类别一个受控燃料列表；配置仅作模板输入契约。
        fuel_col = 172 + n
        for row, (_value, label) in enumerate(CONTRACT.options(c.category_id, "fuel") or (("", ""),), 2):
            put(row, column_letter(fuel_col), label)
    workbook = _parse_xml(data["xl/workbook.xml"])
    names = workbook.find(_tag("definedNames"))
    old_names = set(identity_defined_names(V66_TEMPLATE_ENTRY))
    for node in list(names):
        if node.get("name") in old_names or node.get(
                "name", "").startswith("EV_BOILER_V67_"):
            names.remove(node)
    for name, col, count in ((CATEGORY_NAME, "FL", len(CONTRACT.categories)), (CATEGORY_IDS, "FM", len(CONTRACT.categories))):
        ET.SubElement(names, _tag("definedName"), name=name).text = f"'配置'!${col}$2:${col}${count + 1}"
    for n, c in enumerate(CONTRACT.categories, 1):
        col = column_letter(173 + n)
        count = max(1, len(CONTRACT.options(c.category_id, "fuel")))
        ET.SubElement(names, _tag("definedName"), name=f"EV_BOILER_V67_FUEL_{n}").text = f"'配置'!${col}$2:${col}${count + 1}"
    for name, value in identity_defined_names(entry).items():
        ET.SubElement(
            names,
            _tag("definedName"),
            name=name).text = f'"{value}"'
    _set_inline(root.find(f".//{_tag('c')}[@r='M2']"), "等级限值")
    for r in root.find(_tag("sheetData")):
        if int(r.get("r")) == 3:
            r.set("ht", "90")
    for n in root.find(_tag("cols")):
        if n.get("min") == "6": n.set("width", "52")
        if n.get("min") == "15": n.set("width", "29")
    styles_xml = _capacity_styles(root, data["xl/styles.xml"])
    replacements = {
        "xl/styles.xml": styles_xml,
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
                             if e["template_version"] != "V6.7"] + [entry]
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
