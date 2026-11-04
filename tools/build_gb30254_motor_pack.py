"""只读批准的六表工作簿，生成尚未接入产品的 GB 30254 候选包。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from decimal import Decimal
import xml.etree.ElementTree as ET
import zipfile

from tools.build_gb18613_motor_pack import (
    _cell_text, _column, _q, _shared_strings, _sheet_names, _style_number_formats, NS_MAIN,
)

ROOT = Path(__file__).resolve().parents[1]
MAPPING = Path("docs/standards/gb30254_2024/STANDARD_MAPPING.md")
WORKBOOK = Path("docs/standards/gb30254_2024/data/GB30254_2024_标准表值.xlsx")
OUTPUT = Path("specs/equipment_efficiency/standards/gb30254_2024_candidate.json")
MAPPING_SHA = "6d208c61176461f32a5076dbf8d367b1afd0efab315bf1aad8a8e48e6e5819ba"
WORKBOOK_SHA = "b3755111a4f20a7f4cf1a6e37e48a4e17d4e0dcb8cea2ab88211fc67cf822912"


def build_pack(root: Path = ROOT) -> dict:
    sources = {}
    for label, path, expected in (("mapping", MAPPING, MAPPING_SHA), ("workbook", WORKBOOK, WORKBOOK_SHA)):
        digest = hashlib.sha256((root / path).read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"批准源资产哈希不一致：{path}")
        sources[label] = {"path": path.as_posix(), "sha256": digest}
    tables = []
    numeric, dashes = 0, 0
    with zipfile.ZipFile(root / WORKBOOK) as archive:
        strings, names = _shared_strings(archive), _sheet_names(archive)
        formats = _style_number_formats(archive)
        for number, last_row in enumerate((50, 49, 42, 42, 32, 31), 1):
            sheet = f"表{number}"
            xml = ET.fromstring(archive.read(names[sheet]))
            cells = {c.attrib["r"]: c for c in xml.iter(_q(NS_MAIN, "c"))}
            poles = (2, 4, 6, 8, 10, 12) if number <= 4 else (2, 4, 6, 8)
            rows = []
            for row in range(8, last_row + 1):
                power = _cell_text(cells.get(f"A{row}"), strings)
                if not power.isdecimal() or int(power) <= 0:
                    raise ValueError(f"功率格无效：{sheet}!A{row}")
                branches = {}
                for index, pole in enumerate(poles):
                    thresholds = []
                    for grade in range(3):
                        address = f"{_column(2 + 3 * index + grade)}{row}"
                        text = _cell_text(cells.get(address), strings)
                        if text == "—":
                            dashes += 1
                            value = None
                            display = text
                        else:
                            value = Decimal(text)
                            if not value.is_finite() or not 1 <= value <= 100:
                                raise ValueError(f"效率格无效：{sheet}!{address}")
                            # 原始XML词法保存十进制精度，不经浮点或重存Excel。
                            value = text
                            numeric += 1
                            fmt = formats[int(cells[address].attrib.get("s", "0"))]
                            if fmt not in ("0", "0.0"):
                                raise ValueError(f"未经核验的显示格式：{sheet}!{address}")
                            display = format(Decimal(text), ".1f" if fmt == "0.0" else ".0f")
                            if Decimal(display) != Decimal(text):
                                raise ValueError(f"显示格式隐含舍入：{sheet}!{address}")
                        thresholds.append({"value": value, "source_text": text,
                                           "source_display": display,
                                           "source_cell": f"{sheet}!{address}"})
                    branches[str(pole)] = thresholds
                rows.append({"power_kw": power, "source_cell": f"{sheet}!A{row}", "branches": branches})
            tables.append({"table_number": number, "poles": list(poles), "rows": rows})
    if (numeric, dashes, sum(len(t["rows"]) for t in tables)) != (3093, 285, 204):
        raise ValueError("六表源格清单不符合A.3映射")
    pack = {"schema_version": "equipeffi.motor-hv-candidate.v1", "standard_id": "GB30254-2024",
            "numeric_profile_id": "EQUIPEFFI_MOTOR_HV_EXACT_LINEAR_V1", "source_files": sources,
            "counts": {"numeric": numeric, "horizontal_dash": dashes, "rows": 204}, "tables": tables}
    pack["integrity_sha256"] = hashlib.sha256(json.dumps(pack, ensure_ascii=False, sort_keys=True,
                                                       separators=(",", ":")).encode()).hexdigest()
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / OUTPUT)
    args = parser.parse_args()
    pack = build_pack()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(pack["counts"]))


if __name__ == "__main__":
    main()
