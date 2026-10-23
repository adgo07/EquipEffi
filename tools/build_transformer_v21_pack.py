"""Derive the GB 20052—2024 V2.1 runtime pack from the frozen source pair.

This build tool reads only the 35 per-table worksheets in the approved review
workbook. It deliberately does not open or rewrite an XLSX with an authoring
library, and it never reads the historical flat sheet or legacy JSON.
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
MAPPING_RELATIVE_PATH = Path(
    "docs/standards/gb20052_v21/GB20052_变压器主映射表_V2.1.md"
)
WORKBOOK_RELATIVE_PATH = Path(
    "docs/standards/gb20052_v21/GB20052_2024_变压器表1-35人工校对数据工作簿_V2.1.xlsx"
)
DEFAULT_OUTPUT = Path(
    "src/equipeffi/resources/standards/gb20052_2024_v21.json"
)

EXPECTED_MAPPING_SHA256 = (
    "5934A9112AEE783B8B0335DB8BBEAD480BDE773C5E4FF365A137E7F9F3C1AE24"
)
EXPECTED_WORKBOOK_SHA256 = (
    "35A499BB5406588CDC300C5019BFFD0DE428D3E08CBA21D076CCC8B6F69F2565"
)
STANDARD_PDF_SHA256 = (
    "862D32069301BB76BCF1477E38BEFDCC32DFB219A409032C41FF374E88863A3F"
)
PACK_SCHEMA_VERSION = "equipeffi.transformer-standard-pack.v1"
PACK_ID = "GB20052-2024-TRANSFORMER-V2.1"
PACK_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"
EXPECTED_TOTAL_ROWS = 589
EXPECTED_THRESHOLD_VALUES = 3534

EXPECTED_TABLE_ROW_COUNTS = {
    1: 76,
    2: 114,
    3: 11,
    4: 11,
    5: 14,
    6: 11,
    7: 16,
    8: 11,
    9: 11,
    10: 11,
    11: 11,
    12: 16,
    13: 10,
    14: 9,
    15: 12,
    16: 9,
    17: 9,
    18: 9,
    19: 5,
    20: 6,
    21: 6,
    22: 6,
    23: 6,
    24: 6,
    25: 10,
    26: 15,
    27: 15,
    28: 15,
    29: 7,
    30: 21,
    31: 10,
    32: 27,
    33: 15,
    34: 39,
    35: 9,
}

EXPECTED_HEADERS = (
    "复核行ID（新增行临时）",
    "额定容量(kVA)",
    "铁心材料",
    "联结组别",
    "耐热等级",
    "损耗分支",
    "空载损耗1级",
    "负载损耗1级",
    "空载损耗2级",
    "负载损耗2级",
    "空载损耗3级",
    "负载损耗3级",
    "P0单位",
    "Pk单位",
    "负载损耗参考温度",
    "阻抗/技术条件",
    "PDF物理页/印刷页",
    "校对状态",
    "校对意见",
)

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


class PackBuildError(ValueError):
    """The frozen source pair cannot safely produce the expected runtime pack."""


def _qname(namespace: str, local_name: str) -> str:
    return f"{{{namespace}}}{local_name}"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _mapping_sha256(path: Path) -> str:
    # The frozen text identity is defined over UTF-8/LF bytes. Git's Windows
    # checkout may materialize CRLF, so normalize only line endings first.
    text = path.read_bytes().decode("utf-8")
    return _sha256_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise PackBuildError(f"非有限Decimal不能进入运行包: {value}")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _column(address: str) -> str:
    match = re.match(r"[A-Z]+", address)
    if not match:
        raise PackBuildError(f"无效的XLSX单元格坐标: {address}")
    return match.group(0)


def _sheet_target_path(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join("xl", target))


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    name = "xl/sharedStrings.xml"
    if name not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(name))
    return [
        "".join(node.text or "" for node in item.iter(_qname(NS_MAIN, "t")))
        for item in root.findall(_qname(NS_MAIN, "si"))
    ]


def _cell_text(cell: ET.Element | None, shared_strings: list[str]) -> str:
    if cell is None:
        return ""
    if cell.find(_qname(NS_MAIN, "f")) is not None:
        raise PackBuildError(f"冻结数值源不允许公式单元格: {cell.attrib.get('r')}")
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(_qname(NS_MAIN, "is"))
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iter(_qname(NS_MAIN, "t")))
    value = cell.find(_qname(NS_MAIN, "v"))
    if value is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(value.text or "")]
        except (ValueError, IndexError) as exc:
            raise PackBuildError(f"共享字符串索引无效: {cell.attrib.get('r')}") from exc
    return value.text or ""


def _parse_decimal(raw: str, *, coordinate: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise PackBuildError(f"{coordinate}不是有效十进制数: {raw!r}") from exc
    if not value.is_finite():
        raise PackBuildError(f"{coordinate}不是有限十进制数: {raw!r}")
    return value


def _normalized_conditions(
    table_no: int, raw: dict[str, str]
) -> dict[str, str | None]:
    core_map = {"电工钢带": "electrical_steel", "非晶合金": "amorphous_alloy"}
    vector_map = {"Dyn11/Yzn11": "dyn11_yzn11", "Yyn0": "yyn0"}
    thermal_map = {"B(100℃)": "B", "F(120℃)": "F", "H(145℃)": "H"}
    uk_map = {
        "4.0%": "uk_4_0",
        "6.0%～8.0%": "uk_6_0_to_8_0",
    }
    loss_map = {
        "普通组": "ordinary",
        "低压66/69kV特殊组": "lv_66_69_special",
    }

    core = raw["core_material"]
    vector = raw["vector_group"]
    thermal = raw["thermal_class"]
    loss_branch = raw["loss_branch"]

    normalized: dict[str, str | None] = {
        "core_material": core_map.get(core) if core else None,
        "vector_group": vector_map.get(vector) if vector else None,
        "thermal_class": thermal_map.get(thermal) if thermal else None,
        "uk_group": None,
        "loss_group": None,
    }
    if core and normalized["core_material"] is None:
        raise PackBuildError(f"表{table_no:02d}未知铁心枚举: {core}")
    if vector and normalized["vector_group"] is None:
        raise PackBuildError(f"表{table_no:02d}未知联结组枚举: {vector}")
    if thermal and normalized["thermal_class"] is None:
        raise PackBuildError(f"表{table_no:02d}未知耐热等级枚举: {thermal}")

    if table_no == 2:
        if loss_branch not in uk_map:
            raise PackBuildError(f"表02未知阻抗分支: {loss_branch!r}")
        normalized["uk_group"] = uk_map[loss_branch]
    elif table_no in {27, 28}:
        if loss_branch not in {"A", "B", "C"}:
            raise PackBuildError(f"表{table_no:02d}未知阻抗组: {loss_branch!r}")
        normalized["uk_group"] = loss_branch
    elif table_no == 15:
        if loss_branch not in loss_map:
            raise PackBuildError(f"表15未知低压组: {loss_branch!r}")
        normalized["loss_group"] = loss_map[loss_branch]
    elif table_no == 1:
        if loss_branch not in {"", "Pk合并原格共享"}:
            raise PackBuildError(f"表01未知源格关系标记: {loss_branch!r}")
    elif loss_branch:
        raise PackBuildError(f"表{table_no:02d}出现未建模的损耗分支标签: {loss_branch!r}")

    if table_no in {30, 32, 34} and normalized["thermal_class"] is None:
        raise PackBuildError(f"表{table_no:02d}缺少必需耐热等级")
    return normalized


def _branch_id(table_no: int, conditions: dict[str, str | None]) -> str:
    table_id = f"GB20052-T{table_no:02d}"
    if table_no == 1:
        core = conditions["core_material"]
        vector = conditions["vector_group"]
        if not core or not vector:
            raise PackBuildError("表01每行必须显式具有铁心材料和联结组")
        return f"{table_id}/core={core}/vector={vector}"
    if table_no == 2:
        core = conditions["core_material"]
        thermal = conditions["thermal_class"]
        uk_group = conditions["uk_group"]
        if not core or not thermal or not uk_group:
            raise PackBuildError("表02每行必须显式具有铁心、耐热等级及阻抗组")
        return f"{table_id}/core={core}/thermal={thermal}/uk_group={uk_group}"
    if table_no == 15:
        loss_group = conditions["loss_group"]
        if not loss_group:
            raise PackBuildError("表15每行必须显式具有普通/低压特殊组")
        return f"{table_id}/loss_group={loss_group}"
    if table_no in {27, 28}:
        uk_group = conditions["uk_group"]
        if not uk_group:
            raise PackBuildError(f"表{table_no:02d}每行必须显式具有A/B/C阻抗组")
        return f"{table_id}/uk_group={uk_group}"
    if table_no in {30, 32, 34}:
        thermal = conditions["thermal_class"]
        if not thermal:
            raise PackBuildError(f"表{table_no:02d}每行必须显式具有耐热等级")
        return f"{table_id}/thermal={thermal}"
    return f"{table_id}/default"


def _threshold_pairs(raw_values: list[str], units: dict[str, str], row_number: int) -> tuple[dict[str, Any], dict[str, Any]]:
    grades = ("grade_1", "grade_2", "grade_3")
    source: dict[str, Any] = {}
    normalized: dict[str, Any] = {}
    scale_by_unit = {"W": Decimal(1), "kW": Decimal(1000)}
    no_load_scale = scale_by_unit.get(units["no_load_loss"])
    load_scale = scale_by_unit.get(units["load_loss"])
    if no_load_scale is None or load_scale is None:
        raise PackBuildError(
            f"第{row_number}行的损耗单位必须为W/kW，实际为{units}"
        )
    for index, grade in enumerate(grades):
        no_load_raw = raw_values[index * 2]
        load_raw = raw_values[index * 2 + 1]
        no_load = _parse_decimal(no_load_raw, coordinate=f"row{row_number}:threshold[{grade}].no_load_loss")
        load = _parse_decimal(load_raw, coordinate=f"row{row_number}:threshold[{grade}].load_loss")
        if no_load < 0 or load < 0:
            raise PackBuildError(f"第{row_number}行损耗阈值不得为负数")
        source[grade] = {"no_load_loss": no_load_raw, "load_loss": load_raw}
        normalized[grade] = {
            "no_load_loss": _decimal_text(no_load * no_load_scale),
            "load_loss": _decimal_text(load * load_scale),
        }
    return source, normalized


def _canonical_payload_bytes(pack_without_integrity: dict[str, Any]) -> bytes:
    return json.dumps(
        pack_without_integrity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def payload_sha256(pack: dict[str, Any]) -> str:
    payload = {key: value for key, value in pack.items() if key != "integrity"}
    return _sha256_bytes(_canonical_payload_bytes(payload))


def verify_pack_integrity(pack: dict[str, Any]) -> bool:
    integrity = pack.get("integrity")
    return (
        isinstance(integrity, dict)
        and integrity.get("algorithm") == "sha256"
        and integrity.get("scope") == "canonical UTF-8 JSON excluding integrity"
        and integrity.get("payload_sha256") == payload_sha256(pack)
    )


def _read_workbook_sheets(path: Path) -> dict[int, dict[str, Any]]:
    expected_sheet_names = {f"表{number:02d}" for number in range(1, 36)}
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target_by_id = {
            relationship.attrib["Id"]: relationship.attrib["Target"]
            for relationship in relationships.findall(_qname(NS_PACKAGE_REL, "Relationship"))
        }
        shared_strings = _read_shared_strings(archive)
        worksheets: dict[str, str] = {}
        for sheet in workbook.findall(f"{_qname(NS_MAIN, 'sheets')}/{_qname(NS_MAIN, 'sheet')}"):
            relationship_id = sheet.attrib.get(_qname(NS_REL, "id"))
            if relationship_id not in target_by_id:
                raise PackBuildError(f"Sheet {sheet.attrib.get('name')}缺少工作簿关系")
            worksheets[sheet.attrib["name"]] = _sheet_target_path(target_by_id[relationship_id])

        missing_sheets = expected_sheet_names - worksheets.keys()
        if missing_sheets:
            raise PackBuildError(f"冻结工作簿缺少逐表Sheet: {sorted(missing_sheets)}")

        result: dict[int, dict[str, Any]] = {}
        for table_no in range(1, 36):
            sheet_name = f"表{table_no:02d}"
            root = ET.fromstring(archive.read(worksheets[sheet_name]))
            rows_by_number: dict[int, dict[str, tuple[str, str]]] = {}
            for row in root.findall(f"{_qname(NS_MAIN, 'sheetData')}/{_qname(NS_MAIN, 'row')}"):
                row_number = int(row.attrib["r"])
                cells: dict[str, tuple[str, str]] = {}
                for cell in row.findall(_qname(NS_MAIN, "c")):
                    address = cell.attrib["r"]
                    cells[_column(address)] = (address, _cell_text(cell, shared_strings))
                rows_by_number[row_number] = cells

            def cell(row_number: int, column: str) -> tuple[str, str]:
                entry = rows_by_number.get(row_number, {}).get(column)
                return entry if entry is not None else (f"{column}{row_number}", "")

            title = cell(1, "A")[1]
            headers = tuple(cell(3, column)[1] for column in "ABCDEFGHIJKLMNOPQRS")
            if headers != EXPECTED_HEADERS:
                raise PackBuildError(
                    f"{sheet_name}!A3:S3表头不符合冻结布局: {headers!r}"
                )

            data_rows: list[dict[str, Any]] = []
            for row_number in sorted(rows_by_number):
                if row_number < 4:
                    continue
                row_cells = rows_by_number[row_number]
                source_row_id = cell(row_number, "A")[1].strip()
                capacity_text = cell(row_number, "B")[1].strip()
                threshold_texts = [cell(row_number, column)[1].strip() for column in "GHIJKL"]
                any_body_values = bool(capacity_text or any(threshold_texts))
                if not source_row_id:
                    if any_body_values:
                        raise PackBuildError(
                            f"{sheet_name}第{row_number}行存在容量/阈值但没有源行ID"
                        )
                    continue
                if not re.fullmatch(r"GB20052-R\d{6}", source_row_id):
                    raise PackBuildError(
                        f"{sheet_name}!A{row_number}源行ID格式异常: {source_row_id!r}"
                    )
                if not capacity_text or any(not item for item in threshold_texts):
                    raise PackBuildError(
                        f"{sheet_name}第{row_number}行容量与G:L六阈值必须完整"
                    )

                capacity = _parse_decimal(capacity_text, coordinate=f"{sheet_name}!B{row_number}")
                if capacity <= 0:
                    raise PackBuildError(f"{sheet_name}!B{row_number}额定容量必须大于0")

                raw_conditions = {
                    "core_material": cell(row_number, "C")[1].strip() or "",
                    "vector_group": cell(row_number, "D")[1].strip() or "",
                    "thermal_class": cell(row_number, "E")[1].strip() or "",
                    "loss_branch": cell(row_number, "F")[1].strip() or "",
                }
                conditions = _normalized_conditions(table_no, raw_conditions)
                branch_id = _branch_id(table_no, conditions)
                source_units = {
                    "no_load_loss": cell(row_number, "M")[1].strip(),
                    "load_loss": cell(row_number, "N")[1].strip(),
                }
                thresholds_source, thresholds_w = _threshold_pairs(
                    threshold_texts, source_units, row_number
                )

                grade_cell_columns = (
                    ("G", "H"),
                    ("I", "J"),
                    ("K", "L"),
                )
                threshold_cells = {
                    f"grade_{index + 1}": {
                        "no_load_loss": cell(row_number, pair[0])[0],
                        "load_loss": cell(row_number, pair[1])[0],
                    }
                    for index, pair in enumerate(grade_cell_columns)
                }
                condition_cells = {
                    "core_material": cell(row_number, "C")[0],
                    "vector_group": cell(row_number, "D")[0],
                    "thermal_class": cell(row_number, "E")[0],
                    "loss_branch": cell(row_number, "F")[0],
                }
                data_rows.append(
                    {
                        "source_row_id": source_row_id,
                        "capacity_kva": capacity_text,
                        "branch_id": branch_id,
                        "conditions": conditions,
                        "thresholds_w": thresholds_w,
                        "source": {
                            "sheet": sheet_name,
                            "row": row_number,
                            "cell_coordinates": {
                                "capacity_kva": cell(row_number, "B")[0],
                                "thresholds": threshold_cells,
                                "condition_values": condition_cells,
                                "source_units": {
                                    "no_load_loss": cell(row_number, "M")[0],
                                    "load_loss": cell(row_number, "N")[0],
                                },
                                "load_reference_temperature": cell(row_number, "O")[0],
                                "technical_condition": cell(row_number, "P")[0],
                                "page_reference": cell(row_number, "Q")[0],
                            },
                            "source_thresholds": thresholds_source,
                            "source_units": source_units,
                            "condition_values": raw_conditions,
                            "load_reference_temperature": cell(row_number, "O")[1].strip() or None,
                            "technical_condition_text": cell(row_number, "P")[1].strip() or None,
                            "page_reference": cell(row_number, "Q")[1].strip() or None,
                            "value_status": "explicit",
                            "shared_source_label": (
                                raw_conditions["loss_branch"]
                                if table_no == 1 and raw_conditions["loss_branch"]
                                else None
                            ),
                        },
                    }
                )

            if len(data_rows) != EXPECTED_TABLE_ROW_COUNTS[table_no]:
                raise PackBuildError(
                    f"{sheet_name}源行数为{len(data_rows)}，预期{EXPECTED_TABLE_ROW_COUNTS[table_no]}"
                )
            result[table_no] = {
                "table_no": table_no,
                "table_id": f"GB20052-T{table_no:02d}",
                "route_id": f"GB20052-T{table_no:02d}",
                "source_sheet": sheet_name,
                "title": title,
                "rows": data_rows,
            }
    return result


def build_pack(
    mapping_path: Path | str | None = None,
    workbook_path: Path | str | None = None,
) -> dict[str, Any]:
    mapping_file = Path(mapping_path) if mapping_path is not None else ROOT / MAPPING_RELATIVE_PATH
    workbook_file = Path(workbook_path) if workbook_path is not None else ROOT / WORKBOOK_RELATIVE_PATH
    mapping_sha = _mapping_sha256(mapping_file)
    workbook_sha = _sha256_bytes(workbook_file.read_bytes())
    if mapping_sha != EXPECTED_MAPPING_SHA256:
        raise PackBuildError(
            f"冻结主映射SHA不匹配: {mapping_sha} != {EXPECTED_MAPPING_SHA256}"
        )
    if workbook_sha != EXPECTED_WORKBOOK_SHA256:
        raise PackBuildError(
            f"冻结工作簿SHA不匹配: {workbook_sha} != {EXPECTED_WORKBOOK_SHA256}"
        )

    tables_by_number = _read_workbook_sheets(workbook_file)
    tables = [tables_by_number[number] for number in range(1, 36)]
    source_rows = [row for table in tables for row in table["rows"]]
    source_ids = [row["source_row_id"] for row in source_rows]
    if len(source_rows) != EXPECTED_TOTAL_ROWS:
        raise PackBuildError(
            f"源行总数为{len(source_rows)}，预期{EXPECTED_TOTAL_ROWS}"
        )
    if len(set(source_ids)) != len(source_ids):
        raise PackBuildError("35表源行ID存在重复")
    if sum(len(row["thresholds_w"]) * 2 for row in source_rows) != EXPECTED_THRESHOLD_VALUES:
        raise PackBuildError("35表阈值数值总数不为3534")

    pack: dict[str, Any] = {
        "schema_version": PACK_SCHEMA_VERSION,
        "pack_id": PACK_ID,
        "pack_version": PACK_VERSION,
        "standard_code": "GB 20052-2024",
        "standard_name": "电力变压器能效限定值及能效等级",
        "effective_date": "2025-02-01",
        "mapping_revision": "V2.1",
        "runtime_loss_unit": "W",
        "source_files": {
            "standard_pdf_sha256": STANDARD_PDF_SHA256,
            "mapping": {
                "path": MAPPING_RELATIVE_PATH.as_posix(),
                "sha256": mapping_sha,
            },
            "workbook": {
                "path": WORKBOOK_RELATIVE_PATH.as_posix(),
                "sha256": workbook_sha,
            },
        },
        "generator": {
            "name": "tools/build_transformer_v21_pack.py",
            "version": GENERATOR_VERSION,
        },
        "counts": {
            "tables": 35,
            "threshold_rows": EXPECTED_TOTAL_ROWS,
            "threshold_values": EXPECTED_THRESHOLD_VALUES,
        },
        "tables": tables,
    }
    pack["integrity"] = {
        "algorithm": "sha256",
        "scope": "canonical UTF-8 JSON excluding integrity",
        "payload_sha256": payload_sha256(pack),
    }
    return pack


def _render_json(pack: dict[str, Any]) -> str:
    return json.dumps(pack, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / DEFAULT_OUTPUT,
        help="运行数据包JSON输出路径",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="仅核对现有运行包与冻结源可重复派生结果一致，不写文件",
    )
    args = parser.parse_args(argv)
    try:
        pack = build_pack()
        output_path = args.output if args.output.is_absolute() else ROOT / args.output
        rendered = _render_json(pack)
        if args.check:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            if existing != pack:
                raise PackBuildError(f"现有运行包与冻结源派生内容不同: {output_path}")
            if not verify_pack_integrity(existing):
                raise PackBuildError(f"现有运行包payload哈希无效: {output_path}")
            print(
                f"OK: tables=35 rows={EXPECTED_TOTAL_ROWS} "
                f"threshold_values={EXPECTED_THRESHOLD_VALUES} "
                f"payload_sha256={pack['integrity']['payload_sha256']}"
            )
            return 0
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8", newline="\n")
        print(
            f"Wrote {output_path}: tables=35 rows={EXPECTED_TOTAL_ROWS} "
            f"threshold_values={EXPECTED_THRESHOLD_VALUES} "
            f"payload_sha256={pack['integrity']['payload_sha256']}"
        )
        return 0
    except (OSError, ET.ParseError, zipfile.BadZipFile, PackBuildError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
