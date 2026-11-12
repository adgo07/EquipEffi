"""只读已核验六表，保留全部源格、横杠和液冷分支。"""
from pathlib import Path
from hashlib import sha256
import json
import zipfile
import xml.etree.ElementTree as ET
from fractions import Fraction
from tools.build_gb18613_motor_pack import _cell_text, _shared_strings, _sheet_names, _q, NS_MAIN
ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = Path("docs/standards/gb19153_2019/data/GB19153_2019_标准表值.xlsx")
SOURCE_SHA = "7686bbc675e3f3189b4d21898738dd4f4303e57cf66e0df8db52bbdc89dd7dc7"
OUTPUT = Path("src/equipeffi/resources/standards/gb19153_2019_candidate.json")


def build_pack(root=ROOT):
    source = root / WORKBOOK
    if sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("空压机已核验源表哈希不一致")
    tables = []
    numeric = dashes = 0
    with zipfile.ZipFile(source) as z:
        strings, names = _shared_strings(z), _sheet_names(z)
        for number, last in enumerate((1013, 761, 437, 308, 215, 215), 1):
            name = f"表{number}"
            xml = ET.fromstring(z.read(names[name]))
            cells = {c.attrib["r"]: c for c in xml.iter(_q(NS_MAIN, "c"))}
            rows = []
            for row in range(6, last + 1):
                values = [
                    _cell_text(
                        cells.get(
                            f"{col}{row}"),
                        strings) for col in "ABCDEFGHIJKLMN"]
                power, condition, grade, pressure, cooling, kind, value, unit, pdf, printed, source_row, source_col, bounds, literal = values
                if not all((power, grade, pressure,
                           cooling, kind, value, literal)):
                    raise ValueError(f"源格缺失：{name}!G{row}")
                branch = {
                    "风冷": "AIR",
                    "液冷": "LIQUID",
                    "表内非括号值": "AIR",
                    "表内未分冷却": "NOT_APPLICABLE"}[cooling]
                if value == "—":
                    dashes += 1
                    parsed = None
                else:
                    if Fraction(value) <= 0:
                        raise ValueError(f"非正限值：{name}!G{row}")
                    numeric += 1
                    parsed = value
                # 表值工作簿G列数值XML可能不带末尾0，原N列字面保存标准显示。
                display = (literal.split("[")[1].rstrip(
                    "]") if branch == "LIQUID" and "[" in literal else literal.split("[")[0]) if parsed else "—"
                if parsed and Fraction(display) != Fraction(parsed):
                    raise ValueError(f"显示值改变限值：{name}!G{row}")
                rows.append(dict(power_kw=power, pressure_mpa=pressure, grade=int(grade), cooling=branch, value=parsed,
                                 source_display=display, source_text=literal, source_cell=f"{name}!G{row}", source_kind=kind,
                                 source_pdf_page=int(pdf), source_printed_page=int(printed), source_table_row=int(source_row),
                                 source_table_column=int(source_col), source_bounds=bounds, actual_input_condition=condition))
            tables.append(dict(table_number=number, rows=rows))
    if (numeric, dashes) != (2502, 417):
        raise ValueError("六表源格清单不符已核验基线")
    pack = dict(schema_version="equipeffi.compressor-candidate.v1", standard_id="GB19153-2019",
                numeric_profile_id="EQUIPEFFI_COMPRESSOR_EXACT_LOOKUP_V1", source_files={"workbook": {"path": WORKBOOK.as_posix(), "sha256": SOURCE_SHA}},
                counts={"numeric": numeric, "horizontal_dash": dashes}, tables=tables)
    pack["integrity_sha256"] = sha256(
        json.dumps(
            pack,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":")).encode()).hexdigest()
    return pack


if __name__ == "__main__":
    pack = build_pack()
    (ROOT / OUTPUT).write_text(json.dumps(pack, ensure_ascii=False,
                                          indent=2) + "\n", encoding="utf-8", newline="\n")
    print(pack["counts"])
