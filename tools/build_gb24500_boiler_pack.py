"""从固定SHA源表派生；不修改源件或主映射。"""
from pathlib import Path
from hashlib import sha256
import json
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from tools.build_gb18613_motor_pack import _cell_text, _shared_strings, _sheet_names, _q, NS_MAIN

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = Path("docs/standards/gb24500_2020/data/GB24500_2020_TABLE_VALUES.xlsx")
SOURCE_SHA = "9f8e243b96ea45cd0c1f1a33dc1c0a7b62eaa8a5f2f9095234c427463a68de1a"
OUTPUT = Path("src/equipeffi/resources/standards/gb24500_2020_candidate.json")


def build_pack(root=ROOT):
    source = root / WORKBOOK
    if sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("锅炉已核验源表身份不一致")
    cells = []
    with ZipFile(source) as z:
        strings, names = _shared_strings(z), _sheet_names(z)
        for number, sheet in enumerate(tuple(names)[:4], 1):
            xml = ET.fromstring(z.read(names[sheet]))
            byref = {c.get("r"): c for c in xml.iter(_q(NS_MAIN, "c"))}
            last = (23, 26, 8, 20)[number - 1]
            for row in range(6, last + 1):
                text = lambda col: _cell_text(byref.get(f"{col}{row}"), strings)
                for col in ("FG" if number in {1, 3} else "F"):
                    cells.append(dict(table_number=number, branch=text("A"), fuel=text("B"),
                        qnet_condition=text("C"), vdaf_condition=text("D"), grade=int(text("E")),
                        capacity_bucket=("SMALL" if col == "F" else "LARGE") if number in {1, 3} else None,
                        value=text(col), source_cell=f"{sheet}!{col}{row}"))
        xml = ET.fromstring(z.read(names["限定值与来源"]))
        byref = {c.get("r"): c for c in xml.iter(_q(NS_MAIN, "c"))}
        electric = _cell_text(byref["B5"], strings)
    if len(cells) != 78 or electric != "97":
        raise ValueError("79源值清单不符")
    pack = dict(schema_version="equipeffi.boiler-candidate.v1", standard_id="GB24500-2020",
        numeric_profile_id="EQUIPEFFI_BOILER_EXACT_LOOKUP_V1", mapping_revision="2026-10-23-owner",
        source_files={"workbook": {"path": WORKBOOK.as_posix(), "sha256": SOURCE_SHA}},
        cells=cells, electric_limit={"value": electric, "source_cell": "限定值与来源!B5", "clause": "5.2"})
    pack["integrity_sha256"] = sha256(json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return pack


if __name__ == "__main__":
    pack = build_pack()
    (ROOT / OUTPUT).write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("78表值 + 97%限定值派生完成")
