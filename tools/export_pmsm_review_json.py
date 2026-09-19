"""从人可读校对册导出GB 30253-2024人工激活记录。

该工具只读取校对册和本轮PDF重建标准包，不会修改任何输入文件。为避免把
尚未逐格复核的标准误标为可用，PMSM的全部平铺记录必须为“正确”；机器包
登记的存疑/无数据单元格必须完成PDF复核；确认无数据时可在校对意见中明确写“无数据”，
建议修订值留空。导出的JSON同时写入29张表及全部效率叶节点的覆盖证明，
可直接交给 :mod:`tools.activate_gb30253_pack`；后者仍会再次校验PDF页码、
原始值、存疑位置和复核路径摘要，形成第二道门禁。

用法示例：

    python tools/export_pmsm_review_json.py review.xlsx review.json \
        --reviewer 张三 --review-date 2026-08-27
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"
STANDARD_CODE = "GB 30253-2024"
REVIEW_STATUSES = {"未校对", "正确", "需修改", "存疑"}
EFFICIENCY_PATH = re.compile(r"^tables\[(\d+)\]\.rows\[(\d+)\]\.efficiency\.([123])\[(\d+)\]$")


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _headers(ws: Any) -> dict[str, int]:
    values = {str(cell.value).strip(): cell.column for cell in ws[3] if cell.value not in (None, "")}
    required = {"标准编号", "表号", "结构化区间", "条款/页码", "校对状态", "建议修订值", "校对意见"}
    missing = sorted(required - values.keys())
    if missing:
        raise ValueError(f"标准数据平铺缺少列: {', '.join(missing)}")
    return values


def _load_pack(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("pack_id") != "gb30253_2024_pdf_verified_v1":
        raise ValueError("输入不是本轮GB 30253-2024 PDF重建包")
    if len(payload.get("tables", [])) != 29:
        raise ValueError("标准包必须包含29张表")
    if payload.get("status") == "active":
        raise ValueError("输入标准包已经是active；无需再次导出激活记录")
    return payload


def _pmsm_rows(ws: Any, columns: dict[str, int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    max_col = max(columns.values())
    for row_number, values in enumerate(ws.iter_rows(min_row=4, max_col=max_col, values_only=True), start=4):
        standard = values[columns["标准编号"] - 1] if len(values) >= columns["标准编号"] else None
        if str(standard or "").strip() != STANDARD_CODE:
            continue
        record = {name: values[column - 1] if len(values) >= column else None for name, column in columns.items()}
        record["row_number"] = row_number
        rows.append(record)
    if not rows:
        raise ValueError("校对册中没有GB 30253-2024记录")
    return rows


def _suspicious_cells(pack: dict[str, Any]) -> list[tuple[int, int, int, int, int]]:
    result: list[tuple[int, int, int, int, int]] = []
    for table_index, table in enumerate(pack["tables"]):
        table_no = int(table["table_no"])
        for row_index, row in enumerate(table.get("rows", [])):
            for flat_index in row.get("suspicious_cells", []) or []:
                flat_index = int(flat_index)
                level, dimension_index = _decode_flat_cell(table, row, flat_index)
                result.append((table_index, table_no, row_index, level, dimension_index))
    return result


def _no_data_cells(pack: dict[str, Any]) -> list[tuple[int, int, int, int, int]]:
    """返回机器包已登记的原文无数据单元格。"""
    result: list[tuple[int, int, int, int, int]] = []
    for table_index, table in enumerate(pack["tables"]):
        table_no = int(table["table_no"])
        for row_index, row in enumerate(table.get("rows", [])):
            for flat_index in row.get("no_data_cells", []) or []:
                flat_index = int(flat_index)
                level, dimension_index = _decode_flat_cell(table, row, flat_index)
                result.append((table_index, table_no, row_index, level, dimension_index))
    return result


def _decode_flat_cell(table: dict[str, Any], row: dict[str, Any], flat_index: int) -> tuple[int, int]:
    """Decode a row-local cell index for both three-grade and single-grade tables.

    The PDF rebuild stores ``suspicious_cells``/``no_data_cells`` as indexes
    into the flattened values extracted from one row.  Tables 8--28 have one
    grade only, so their index starts at zero within that grade; it must not be
    decoded as if three grade arrays had been concatenated.
    """
    dims = table.get("dims", [])
    if not isinstance(dims, list) or not dims:
        raise ValueError(f"表{table.get('table_no')}缺少维度列表")
    efficiency = row.get("efficiency", {})
    if not isinstance(efficiency, dict) or not efficiency:
        raise ValueError(f"表{table.get('table_no')}功率行缺少效率数组")
    grades = [int(key) for key in efficiency if str(key) in {"1", "2", "3"}]
    if len(grades) == 1:
        level = grades[0]
        dimension_index = flat_index
    else:
        level = flat_index // len(dims) + 1
        dimension_index = flat_index % len(dims)
    if level not in (1, 2, 3):
        raise ValueError(f"表{table.get('table_no')}存疑/无数据单元格等级无效: {level}")
    if flat_index < 0 or dimension_index >= len(dims):
        raise ValueError(f"表{table.get('table_no')}存疑/无数据单元格索引越界: {flat_index}")
    return level, dimension_index


def _expected_efficiency_paths(pack: dict[str, Any]) -> set[str]:
    """返回机器包中每个效率叶节点的路径，防止校对册被删行后漏审。"""
    paths: set[str] = set()
    for table_index, table in enumerate(pack["tables"]):
        for row_index, row in enumerate(table.get("rows", [])):
            efficiency = row.get("efficiency", {})
            if not isinstance(efficiency, dict) or not efficiency:
                raise ValueError(f"表{table.get('table_no')}功率行缺少效率数组")
            for level, values in efficiency.items():
                if str(level) not in {"1", "2", "3"} or not isinstance(values, list):
                    raise ValueError(f"表{table.get('table_no')}功率行效率数组无效")
                paths.update(
                    f"tables[{table_index}].rows[{row_index}].efficiency.{level}[{index}]"
                    for index in range(len(values))
                )
    return paths


def _paths_digest(paths: set[str]) -> str:
    return hashlib.sha256("\n".join(sorted(paths)).encode("utf-8")).hexdigest()


def _row_for_path(rows: list[dict[str, Any]], table_index: int, row_index: int, level: int, dimension_index: int) -> dict[str, Any]:
    path = f"tables[{table_index}].rows[{row_index}].efficiency.{level}[{dimension_index}]"
    matches = [row for row in rows if str(row.get("结构化区间") or "").strip() == path]
    if len(matches) != 1:
        raise ValueError(f"校对册未能唯一定位数据路径: {path}")
    return matches[0]


def export_review(review_book: Path, output: Path, reviewer: str, review_date: str, pack_path: Path = DEFAULT_PACK) -> dict[str, Any]:
    reviewer = str(reviewer).strip()
    review_date = str(review_date).strip()
    if not reviewer:
        raise ValueError("reviewer不能为空")
    try:
        date.fromisoformat(review_date)
    except ValueError as exc:
        raise ValueError("review_date必须为YYYY-MM-DD") from exc
    pack = _load_pack(Path(pack_path).resolve())
    workbook = load_workbook(Path(review_book).resolve(), read_only=True, data_only=True)
    try:
        if "标准数据平铺" not in workbook.sheetnames:
            raise ValueError("校对册缺少标准数据平铺sheet")
        ws = workbook["标准数据平铺"]
        columns = _headers(ws)
        rows = _pmsm_rows(ws, columns)
    finally:
        # read_only工作簿仍持有文件句柄；导出流程只需要内存中的值，尽早
        # 关闭它也便于Windows下调用方随后移动或删除校对册。
        workbook.close()
    invalid_status = [row for row in rows if str(row.get("校对状态") or "").strip() not in REVIEW_STATUSES]
    if invalid_status:
        raise ValueError(f"存在未知校对状态（共{len(invalid_status)}行）")
    not_verified = [row for row in rows if str(row.get("校对状态") or "").strip() != "正确"]
    if not_verified:
        examples = ", ".join(str(row["row_number"]) for row in not_verified[:5])
        raise ValueError(f"PMSM仍有{len(not_verified)}行未标记为“正确”，示例Excel行: {examples}")

    present_tables = {str(row.get("表号") or "").strip() for row in rows}
    missing_tables = [f"表{number}" for number in range(1, 30) if f"表{number}" not in present_tables]
    if missing_tables:
        raise ValueError(f"校对册缺少PMSM标准表记录: {', '.join(missing_tables)}")
    expected_paths = _expected_efficiency_paths(pack)
    actual_paths = {
        str(row.get("结构化区间") or "").strip()
        for row in rows
        if EFFICIENCY_PATH.fullmatch(str(row.get("结构化区间") or "").strip())
    }
    if actual_paths != expected_paths:
        missing_paths = sorted(expected_paths - actual_paths)
        extra_paths = sorted(actual_paths - expected_paths)
        detail = f"缺少{len(missing_paths)}条"
        if extra_paths:
            detail += f"，多出{len(extra_paths)}条"
        raise ValueError(f"校对册效率数据与机器包不一致：{detail}")

    suspicious = _suspicious_cells(pack)
    no_data_cells = _no_data_cells(pack)
    items: list[dict[str, Any]] = []
    review_targets = [(item, False) for item in suspicious] + [(item, True) for item in no_data_cells]
    seen_targets: set[tuple[int, int, int, int, int]] = set()
    for (table_index, table_no, row_index, level, dimension_index), registered_no_data in review_targets:
        target = (table_index, table_no, row_index, level, dimension_index)
        if target in seen_targets:
            continue
        seen_targets.add(target)
        table = next(table for table in pack["tables"] if int(table["table_no"]) == table_no)
        row = _row_for_path(rows, table_index, row_index, level, dimension_index)
        status = str(row.get("校对状态") or "").strip()
        if status != "正确":
            raise ValueError(f"存疑单元格Excel行{row['row_number']}必须完成人工校对")
        comment = str(row.get("校对意见") or "").strip()
        if not comment:
            raise ValueError(f"存疑单元格Excel行{row['row_number']}缺少校对意见")
        no_data = registered_no_data or any(token in comment for token in ("无数据", "无资料", "没有数据"))
        replacement = _as_number(row.get("建议修订值"))
        if no_data:
            if replacement is not None:
                raise ValueError(f"存疑单元格Excel行{row['row_number']}标记无数据时建议修订值必须为空")
        elif replacement is None or not 0 < replacement <= 100:
            raise ValueError(f"存疑单元格Excel行{row['row_number']}缺少有效建议修订值（1~100），或在意见中明确标记无数据")
        power_row = table["rows"][row_index]
        if "power_kw" not in power_row:
            raise ValueError(f"表{table_no}第{row_index + 1}行不是固定功率档，不能导出激活记录")
        items.append({
            "table_no": table_no,
            "power_kw": power_row["power_kw"],
            "level": level,
            "dimension": table["dims"][dimension_index],
            "replacement": replacement,
            "no_data": no_data,
            "pdf_page": int(table.get("pages", [])[0]),
            "pdf_checked": True,
            "comment": comment,
            "workbook_row": row["row_number"],
        })

    result = {
        "reviewer": reviewer,
        "review_date": review_date,
        "standard_code": STANDARD_CODE,
        "pack_id": pack["pack_id"],
        "source_sha256": pack.get("source_sha256", ""),
        # 这些字段是激活工具的第二道门禁：只有校对册中全部机器数据
        # 记录为“正确”且路径集合与当前包一致时才会写出true。
        "all_cells_reviewed": True,
        "reviewed_tables": list(range(1, 30)),
        "reviewed_efficiency_cell_count": len(expected_paths),
        "reviewed_paths_sha256": _paths_digest(expected_paths),
        "items": items,
    }
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从PMSM人工校对册导出安全激活记录")
    parser.add_argument("review_book", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--review-date", required=True)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    args = parser.parse_args(argv)
    result = export_review(args.review_book, args.output, args.reviewer, args.review_date, args.pack)
    print(json.dumps({"items": len(result["items"]), "output": str(Path(args.output).resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
