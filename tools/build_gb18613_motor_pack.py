"""Build the GB 18613 six-table runtime pack from the frozen A.1 workbook.

Reads the workbook through zipfile/XML only and refuses source assets whose
SHA-256 or audited source-cell inventory differ from the approved baseline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = Path("docs/standards/gb18613_2020/STANDARD_MAPPING.md")
WORKBOOK_PATH = Path("docs/standards/gb18613_2020/data/GB18613_2020_表1-6校对数据_A1.xlsx")
DEFAULT_OUTPUT = Path("src/equipeffi/resources/standards/gb18613_2020.json")
EXPECTED_MAPPING_SHA256 = "cc566c039d582c48ad0601e76db537b1dbbf2a006e16118eae86f97d88891d61"
EXPECTED_WORKBOOK_SHA256 = "fabb5722cf73afbdaf8fa8c5e76b8eddc86918b4cffe5ce060594afc609164bb"
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
SCHEMA_VERSION = "equipeffi.motor-standard-pack.v1"
PACK_ID = "gb18613_2020_v2"
STANDARD_CODE = "GB 18613-2020"
PROFILE_ID = "EQUIPEFFI_MOTOR_EXACT_LINEAR_V1"

TABLE_SPECS = {
    1: {"rows": range(6, 37), "range": "A6:M36", "power_unit": "kW", "poles": (2, 4, 6, 8)},
    2: {"rows": range(6, 17), "range": "A6:J16", "power_unit": "W", "poles": (2, 4, 6)},
    3: {"rows": range(6, 15), "range": "A6:J14", "power_unit": "W", "poles": (2, 4, 6)},
    4: {"rows": range(6, 15), "range": "A6:G14", "power_unit": "W", "poles": (2, 4)},
    5: {"rows": range(6, 30), "range": "A6:J29", "power_unit": "W", "poles": (4, 6, 8)},
    6: {"rows": range(6, 30), "range": "A6:P29", "power_unit": "W", "rpm_bands": ("r<=500", "500<r<=700", "700<r<=1000", "1000<r<=1300", "r>1300")},
}


class PackBuildError(ValueError):
    """The approved source pair cannot safely produce a motor pack."""


def _q(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise PackBuildError("非有限阈值不能进入GB 18613运行包。")
    result = format(value, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if result in {"", "-0"} else result


def _column(index: int) -> str:
    result = ""
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def _sheet_path(target: str) -> str:
    return target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    name = "xl/sharedStrings.xml"
    if name not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(name))
    return ["".join(node.text or "" for node in item.iter(_q(NS_MAIN, "t"))) for item in root.findall(_q(NS_MAIN, "si"))]


def _cell_text(cell: ET.Element | None, shared: list[str]) -> str:
    if cell is None:
        return ""
    if cell.find(_q(NS_MAIN, "f")) is not None:
        raise PackBuildError(f"源工作簿中不允许公式单元格：{cell.attrib.get('r')}")
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        inline = cell.find(_q(NS_MAIN, "is"))
        return "" if inline is None else "".join(node.text or "" for node in inline.iter(_q(NS_MAIN, "t")))
    value = cell.find(_q(NS_MAIN, "v"))
    if value is None:
        return ""
    raw = value.text or ""
    if kind == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError) as exc:
            raise PackBuildError(f"共享字符串索引无效：{cell.attrib.get('r')}") from exc
    return raw


def _sheet_names(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rel_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {item.attrib["Id"]: _sheet_path(item.attrib["Target"]) for item in rel_root.findall(_q(NS_PKG_REL, "Relationship"))}
    result = {}
    for sheet in workbook.findall(f".//{_q(NS_MAIN, 'sheet')}"):
        relation = sheet.attrib[_q(NS_REL, "id")]
        if relation not in targets:
            raise PackBuildError(f"工作簿工作表关系缺失：{sheet.attrib['name']}")
        result[sheet.attrib["name"]] = targets[relation]
    return result


def _parse_decimal(raw: str, address: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise PackBuildError(f"{address}不是有效十进制数：{raw!r}") from exc
    if not value.is_finite():
        raise PackBuildError(f"{address}不是有限十进制数：{raw!r}")
    return value


_POWER_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:[~～]\s*(\d+(?:\.\d+)?))?\s*$")


def _power_range(raw: str, table_no: int, row_no: int, unit: str) -> dict[str, str]:
    match = _POWER_RE.fullmatch(raw)
    if not match:
        raise PackBuildError(f"表{table_no} A{row_no}功率格式无效：{raw!r}")
    low = _parse_decimal(match.group(1), f"表{table_no}!A{row_no}")
    high = _parse_decimal(match.group(2) or match.group(1), f"表{table_no}!A{row_no}")
    if low <= 0 or high < low:
        raise PackBuildError(f"表{table_no} A{row_no}功率区间无效。")
    factor = Decimal("1000") if unit == "kW" else Decimal("1")
    return {"source_text": raw, "unit": unit, "lower": _decimal_text(low), "upper": _decimal_text(high),
            "normalized_w_lower": _decimal_text(low * factor), "normalized_w_upper": _decimal_text(high * factor)}


def _branches(table_no: int) -> list[dict[str, Any]]:
    spec = TABLE_SPECS[table_no]
    if table_no < 6:
        return [{"branch_id": f"poles_{pole}", "dimension": "poles", "value": pole} for pole in spec["poles"]]
    return [{"branch_id": f"rpm_band_{i}", "dimension": "max_nameplate_speed_rpm", "value": label} for i, label in enumerate(spec["rpm_bands"], 1)]


def _threshold_column(table_no: int, branch_index: int, grade: int) -> int:
    if table_no == 1:
        return 2 + 4 * (grade - 1) + branch_index
    if table_no in (2, 3, 5):
        return 2 + 3 * (grade - 1) + branch_index
    if table_no == 4:
        return 2 + 2 * (grade - 1) + branch_index
    return 2 + 3 * branch_index + (grade - 1)


def _required_basis(table_no: int) -> dict[str, Any]:
    if table_no == 1:
        return {"method": "GB/T 1032 B法（测量输入—输出功率的损耗分析法）", "source_standard": STANDARD_CODE,
                "source_clause": "第6章", "applies_to": "三相异步电动机"}
    result: dict[str, Any] = {"method": "GB/T 5171.21直接法", "source_standard": STANDARD_CODE,
        "source_clause": "第6章", "applies_to": "单相异步电动机" if table_no <= 4 else "空调器风扇用电动机"}
    if table_no in (5, 6):
        result["test_speed_rule"] = "铭牌标称最高转速"
    if table_no == 6:
        result["inseparable_drive_efficiency_rule"] = "按电机与驱动整体效率考核"
    return result


def build_pack(root: Path = ROOT) -> dict[str, Any]:
    mapping_path, workbook_path = root / MAPPING_PATH, root / WORKBOOK_PATH
    if not mapping_path.is_file() or not workbook_path.is_file():
        raise PackBuildError("GB 18613映射或A.1源工作簿不存在。")
    mapping_sha, workbook_sha = _sha(mapping_path.read_bytes()), _sha(workbook_path.read_bytes())
    if mapping_sha != EXPECTED_MAPPING_SHA256 or workbook_sha != EXPECTED_WORKBOOK_SHA256:
        raise PackBuildError("GB 18613映射或源工作簿SHA-256与批准资产不一致。")
    counts = {"AVAILABLE": 0, "HORIZONTAL_DASH": 0, "SOURCE_BLANK": 0}
    tables: list[dict[str, Any]] = []
    with zipfile.ZipFile(workbook_path) as archive:
        shared, sheets = _shared_strings(archive), _sheet_names(archive)
        if not {f"表{i}" for i in range(1, 7)}.issubset(sheets):
            raise PackBuildError("A.1工作簿缺少表1至表6工作表。")
        sheet_cells: dict[int, dict[str, ET.Element]] = {}
        for number in range(1, 7):
            root_xml = ET.fromstring(archive.read(sheets[f"表{number}"]))
            sheet_cells[number] = {cell.attrib["r"]: cell for cell in root_xml.findall(f".//{_q(NS_MAIN, 'c')}")}
        for table_no, spec in TABLE_SPECS.items():
            sheet, cells = f"表{table_no}", sheet_cells[table_no]
            branches, rows = _branches(table_no), []
            for row_no in spec["rows"]:
                address = f"A{row_no}"
                raw_power = _cell_text(cells.get(address), shared).strip()
                if not raw_power:
                    raise PackBuildError(f"源功率格{sheet}!{address}为空。")
                row_id = f"GB18613-T{table_no:02d}-R{row_no:03d}"
                row: dict[str, Any] = {"source_row_id": row_id, "source_row": row_no,
                    "power": _power_range(raw_power, table_no, row_no, spec["power_unit"]) | {"source_sheet": sheet, "source_cell": address},
                    "branches": {}}
                for branch_index, branch in enumerate(branches):
                    by_grade: dict[str, Any] = {}
                    for grade in (1, 2, 3):
                        cell_address = f"{_column(_threshold_column(table_no, branch_index, grade))}{row_no}"
                        text = _cell_text(cells.get(cell_address), shared).strip()
                        if text in {"—", "–", "-", "－"}:
                            source_state, state, value = "HORIZONTAL_DASH", "NO_INDICATOR", None
                        elif text == "":
                            source_state, state, value = "SOURCE_BLANK", "NO_INDICATOR", None
                        else:
                            number = _parse_decimal(text, f"{sheet}!{cell_address}")
                            if number <= 0 or number > 100:
                                raise PackBuildError(f"阈值超出合理数据域：{sheet}!{cell_address}={text}")
                            source_state, state, value = "NUMERIC", "AVAILABLE", _decimal_text(number)
                        counts[state if state == "AVAILABLE" else source_state] += 1
                        by_grade[f"grade_{grade}"] = {"state": state, "source_state": source_state, "source_text": text,
                            "value": value, "source_sheet": sheet, "source_cell": cell_address, "source_row_id": row_id}
                    row["branches"][branch["branch_id"]] = by_grade
                rows.append(row)
            tables.append({"table_id": f"GB18613-T{table_no:02d}", "table_no": table_no, "source_sheet": sheet,
                "source_range": spec["range"], "power_unit": spec["power_unit"], "branches": branches,
                "required_test_basis": _required_basis(table_no), "rows": rows})
    inventory = {"power_rows": sum(len(t["rows"]) for t in tables),
        "threshold_cells": sum(len(t["rows"]) * len(t["branches"]) * 3 for t in tables),
        "threshold_values": counts["AVAILABLE"], "horizontal_dashes": counts["HORIZONTAL_DASH"], "source_blanks": counts["SOURCE_BLANK"]}
    expected = {"power_rows": 108, "threshold_cells": 1182, "threshold_values": 1149, "horizontal_dashes": 32, "source_blanks": 1}
    if inventory != expected:
        raise PackBuildError(f"A.1源格数量与核验基线不一致：{inventory}")
    pack: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "pack_id": PACK_ID, "standard_code": STANDARD_CODE,
        "standard_name": "电动机能效限定值及能效等级", "data_version": "2026.10.25", "mapping_revision": "A.2",
        "source_data_revision": "A.1", "numeric_profile_id": PROFILE_ID,
        "source_files": {"mapping": {"path": MAPPING_PATH.as_posix(), "revision": "A.2", "sha256": mapping_sha},
            "source_workbook": {"path": WORKBOOK_PATH.as_posix(), "revision": "A.1", "sha256": workbook_sha}},
        "counts": inventory, "tables": tables}
    canonical = json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    pack["integrity"] = {"algorithm": "sha256", "canonicalization": "sorted compact UTF-8 JSON excluding integrity",
        "sha256": hashlib.sha256(canonical).hexdigest().upper()}
    return pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        pack = build_pack()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    except (OSError, zipfile.BadZipFile, ET.ParseError, PackBuildError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Built {args.output} ({pack['counts']['threshold_values']} numeric thresholds; sha256={pack['integrity']['sha256']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
