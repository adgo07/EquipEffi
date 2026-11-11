"""Derive the GB 30253 candidate resource from the approved 29-table workbook."""
from __future__ import annotations

import argparse
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from tools.build_gb18613_motor_pack import (
    NS_MAIN, _cell_text, _column, _q, _shared_strings, _sheet_names, _style_number_formats,
)

ROOT = Path(__file__).resolve().parents[1]
MAPPING = Path("docs/standards/gb30253_2024/STANDARD_MAPPING.md")
WORKBOOK = MAPPING.parent / "data/GB30253_2024_TABLE_VALUES.xlsx"
OUTPUT = Path("src/equipeffi/resources/standards/gb30253_2024_candidate.json")
MAPPING_SHA = "3118f05a4fe784e56db36e52ffd25941f2eafadd0a6995e10061541b241c3748"
WORKBOOK_SHA = "34cafd69c14bc5b15d4e674ab7a18b49ec8cc55fe34175a698b827074d2004a1"
PROFILE_ID = "EQUIPEFFI_MOTOR_PMSM_EXACT_LINEAR_V1"
SCHEMA = "equipeffi.motor-pmsm-candidate.v1"
LAST_ROWS = (33,) + (27,) * 6 + (34,) * 3 + (31,) * 18 + (26,)
WIDTHS = (21,) + (15,) * 6 + (14,) * 3 + (15,) * 18 + (21,)
HEADER = re.compile(r"([123])级\n(.+?)(极| r/min)")
DECIMAL_PLACES = {"0": 0, "0.0": 1, "0.00": 2}


def build_pack(root: Path = ROOT) -> dict:
    mapping = (root / MAPPING).read_bytes().replace(b"\r\n", b"\n")
    workbook = root / WORKBOOK
    if sha256(mapping).hexdigest() != MAPPING_SHA or sha256(workbook.read_bytes()).hexdigest() != WORKBOOK_SHA:
        raise ValueError("GB 30253 批准源文件哈希不一致")
    tables = []
    numeric = dashes = 0
    with ZipFile(workbook) as archive:
        strings, names = _shared_strings(archive), _sheet_names(archive)
        formats = _style_number_formats(archive)
        for number, (last_row, width) in enumerate(zip(LAST_ROWS, WIDTHS, strict=True), 1):
            sheet = f"表{number:02}"
            xml = ET.fromstring(archive.read(names[sheet]))
            cells = {cell.attrib["r"]: cell for cell in xml.iter(_q(NS_MAIN, "c"))}

            def source(column: int, row: int, *, formatted: bool = False) -> str:
                address = f"{_column(column)}{row}"
                cell = cells.get(address)
                raw = _cell_text(cell, strings)
                if not raw:
                    raise ValueError(f"批准源格为空：{sheet}!{address}")
                if not formatted or cell.attrib.get("t") in {"inlineStr", "s", "str"}:
                    return raw
                fmt = formats[int(cell.attrib.get("s", "0"))]
                if fmt not in DECIMAL_PLACES:
                    raise ValueError(f"源格数字格式无效：{sheet}!{address}")
                exact = Decimal(raw)
                displayed = format(exact, f".{DECIMAL_PLACES[fmt]}f")
                if Decimal(displayed) != exact:
                    raise ValueError(f"源格格式发生修约：{sheet}!{address}")
                return displayed

            columns = []
            for index in range(2, width + 2):
                heading = source(index, 6)
                parsed = HEADER.fullmatch(heading)
                if parsed is None:
                    raise ValueError(f"批准源表头无效：{sheet}!{_column(index)}6")
                grade, axis, unit = parsed.groups()
                columns.append({"cell": f"{_column(index)}6", "grade": int(grade), "axis": axis,
                                "unit": "count" if unit == "极" else "r/min"})
            rows = []
            for row in range(7, last_row + 1):
                values = [source(column, row, formatted=True) for column in range(2, width + 2)]
                for index, value in enumerate(values, 2):
                    if value == "—":
                        dashes += 1
                        continue
                    numeric += 1
                    if number == 1 and row == 23 and index == 14 and value == "0.0":
                        continue
                    if not re.fullmatch(r"[0-9]+\.[0-9]", value) or not 1 <= Decimal(value) <= 100:
                        raise ValueError(f"批准源效率无效：{sheet}!{_column(index)}{row}")
                rows.append({"row": row, "power_kw": source(1, row, formatted=True), "efficiencies_pct": values,
                             "pdf_page": int(source(width + 2, row)), "printed_page": int(source(width + 3, row)),
                             "pdf_table_on_page": int(source(width + 4, row)),
                             "pdf_row": int(source(width + 5, row))})
            tables.append({"number": number, "sheet": sheet, "columns": columns, "rows": rows})

    if (numeric, dashes, sum(len(table["rows"]) for table in tables)) != (10651, 152, 707):
        raise ValueError("GB 30253 批准源表格数不符")
    pack = {
        "schema_version": SCHEMA, "standard_id": "GB30253-2024", "numeric_profile_id": PROFILE_ID,
        "source_files": {
            "mapping": {"path": MAPPING.as_posix(), "sha256": MAPPING_SHA, "line_endings": "LF"},
            "workbook": {"path": WORKBOOK.as_posix(), "sha256": WORKBOOK_SHA},
        },
        "counts": {"tables": len(tables), "rows": 707, "numeric": numeric, "horizontal_dash": dashes},
        "excluded_cells": {"表01!N23": "EQP-STD-GB30253-001"},
        "tables": tables,
    }
    pack["integrity_sha256"] = sha256(json.dumps(pack, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":")).encode()).hexdigest()
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / OUTPUT)
    args = parser.parse_args()
    pack = build_pack()
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    print(pack["counts"], pack["integrity_sha256"])


if __name__ == "__main__":
    main()
