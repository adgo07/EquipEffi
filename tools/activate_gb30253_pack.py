"""在人工对照PDF后，安全激活GB 30253-2024标准包。

本工具不会修改输入JSON。它要求人可读校对册已经证明29张表的全部效率
单元格逐格复核，并要求每个存疑/无数据单元格都有明确的人工确认记录；记录
包含PDF已核对、复核人、页码和修订值。若PDF确认该单元格无数据，可将
``no_data``设为true且replacement留空。没有这些信息时直接拒绝激活。它
不依据单调趋势或经验值自动修订任何数字。

修订文件示例：

.. code-block:: json

  {
    "reviewer": "张三",
    "review_date": "2026-08-27",
    "all_cells_reviewed": true,
    "reviewed_tables": [1, 2, "…", 29],
    "reviewed_efficiency_cell_count": 10803,
    "reviewed_paths_sha256": "由export_pmsm_review_json.py生成",
    "pack_id": "gb30253_2024_pdf_verified_v1",
    "source_sha256": "与输入标准包一致",
    "items": [{
      "table_no": 1, "power_kw": 55, "level": 2,
      "dimension": 12, "replacement": 94.9,
      "pdf_page": 7, "pdf_checked": true,
      "comment": "已逐格对照PDF原文"
    }]
  }

覆盖字段应优先由 ``export_pmsm_review_json.py`` 自动生成；上例中的省略号和
说明文字不是可直接提交的JSON值。

只有人工确认后才应运行：

    python tools/activate_gb30253_pack.py input.json review.json active.json
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_row(pack: dict[str, Any], item: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    table_no = int(item["table_no"])
    power = float(item["power_kw"])
    level = int(item["level"])
    dimension = item["dimension"]
    tables = [table for table in pack.get("tables", []) if int(table.get("table_no", -1)) == table_no]
    if len(tables) != 1:
        raise ValueError(f"表{table_no}不存在或重复")
    table = tables[0]
    rows = [row for row in table.get("rows", []) if float(row.get("power_kw", float("nan"))) == power]
    if len(rows) != 1:
        raise ValueError(f"表{table_no}中功率{power:g}kW不存在或重复")
    if level not in (1, 2, 3):
        raise ValueError("level必须为1、2或3")
    dims = table.get("dims", [])
    try:
        dim_index = dims.index(dimension)
    except ValueError as exc:
        raise ValueError(f"表{table_no}不存在维度值{dimension!r}") from exc
    values = rows[0].get("efficiency", {}).get(str(level))
    if not isinstance(values, list) or dim_index >= len(values):
        raise ValueError(f"表{table_no}功率{power:g}kW等级{level}没有该维度值")
    return rows[0], dim_index, level


def _expected_efficiency_paths(pack: dict[str, Any]) -> set[str]:
    """Return every efficiency leaf that must have been reviewed.

    Tables 8--28 contain only one of the three grades, so this must iterate
    over the grades actually present in the machine package rather than
    assuming that every row has ``1``, ``2`` and ``3`` arrays.
    """
    paths: set[str] = set()
    for table_index, table in enumerate(pack.get("tables", [])):
        for row_index, row in enumerate(table.get("rows", [])):
            efficiency = row.get("efficiency", {})
            if not isinstance(efficiency, dict) or not efficiency:
                raise ValueError(f"表{table.get('table_no')}功率行缺少效率数据")
            for level, values in efficiency.items():
                if str(level) not in {"1", "2", "3"} or not isinstance(values, list):
                    raise ValueError(f"表{table.get('table_no')}功率行效率结构无效")
                paths.update(
                    f"tables[{table_index}].rows[{row_index}].efficiency.{level}[{index}]"
                    for index in range(len(values))
                )
    return paths


def _paths_digest(paths: set[str]) -> str:
    """Stable digest used to bind the review coverage to this exact package."""
    payload = "\n".join(sorted(paths)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _check_review_coverage(review: dict[str, Any], pack: dict[str, Any]) -> int:
    """Require explicit proof that all 29 tables and all cells were reviewed.

    Reviewing only the machine package's suspicious/no-data cells is not
    sufficient: ordinary cells could have been silently omitted from a
    hand-written review JSON.  The export tool writes these coverage fields
    only after the human-readable workbook has every expected record marked
    ``正确``.
    """
    if review.get("all_cells_reviewed") is not True:
        raise ValueError("人工确认记录必须明确all_cells_reviewed=true，证明29张表已逐格复核")
    expected_tables = list(range(1, 30))
    reviewed_tables = review.get("reviewed_tables")
    try:
        normalized_tables = [int(value) for value in reviewed_tables]
    except (TypeError, ValueError):
        normalized_tables = []
    if normalized_tables != expected_tables:
        raise ValueError("人工确认记录必须覆盖表1至表29，且reviewed_tables不得缺表或重复")
    expected_paths = _expected_efficiency_paths(pack)
    raw_count = review.get("reviewed_efficiency_cell_count")
    # JSON中的覆盖数必须是整数；不能把10803.5、true或任意可转整数的
    # 字符串静默接受为完整复核证明。
    reviewed_count = raw_count if isinstance(raw_count, int) and not isinstance(raw_count, bool) else -1
    if reviewed_count != len(expected_paths):
        raise ValueError(
            f"人工确认记录效率单元格覆盖数不一致：需要{len(expected_paths)}，实际{reviewed_count}"
        )
    digest = str(review.get("reviewed_paths_sha256", "")).strip().lower()
    if digest != _paths_digest(expected_paths):
        raise ValueError("人工确认记录的复核路径摘要与当前标准包不一致")
    if review.get("pack_id") != pack.get("pack_id"):
        raise ValueError("人工确认记录pack_id与输入标准包不一致")
    if str(review.get("source_sha256", "")).strip().lower() != str(pack.get("source_sha256", "")).strip().lower():
        raise ValueError("人工确认记录source_sha256与输入标准包不一致")
    return len(expected_paths)


def activate(input_path: Path, review_path: Path, output_path: Path) -> dict[str, Any]:
    input_path = Path(input_path).resolve()
    review_path = Path(review_path).resolve()
    output_path = Path(output_path).resolve()
    if output_path == input_path:
        raise ValueError("输出文件必须与输入文件不同，禁止覆盖原始标准包")
    pack = _load(input_path)
    review = _load(review_path)
    if pack.get("pack_id") != "gb30253_2024_pdf_verified_v1":
        raise ValueError("输入不是本轮GB 30253-2024 PDF重建包")
    if len(pack.get("tables", [])) != 29:
        raise ValueError("标准包必须包含29张表")
    if pack.get("status") == "active":
        raise ValueError("输入标准包已经是active，不重复激活")
    reviewer = str(review.get("reviewer", "")).strip()
    review_date = str(review.get("review_date", "")).strip()
    if not reviewer or not review_date:
        raise ValueError("人工确认记录必须包含reviewer和review_date")
    try:
        date.fromisoformat(review_date)
    except ValueError as exc:
        raise ValueError("review_date必须为YYYY-MM-DD") from exc
    reviewed_cell_count = _check_review_coverage(review, pack)
    items = review.get("items")
    if not isinstance(items, list):
        raise ValueError("人工确认记录items必须为列表（可为空）")
    suspicious: list[tuple[dict[str, Any], int]] = []
    for table in pack["tables"]:
        for row in table.get("rows", []):
            for index in row.get("suspicious_cells", []):
                suspicious.append((row, int(index)))
    if len(items) < len(suspicious):
        raise ValueError(f"必须逐一确认全部存疑单元格：需要至少{len(suspicious)}项，实际{len(items)}项")

    result = deepcopy(pack)
    applied: list[dict[str, Any]] = []
    seen: set[tuple[int, float, int, Any]] = set()
    for item in items:
        for key in ("table_no", "power_kw", "level", "dimension", "pdf_page", "pdf_checked"):
            if key not in item:
                raise ValueError(f"人工确认记录缺少{key}")
        if item["pdf_checked"] is not True:
            raise ValueError("每项必须明确设置pdf_checked=true")
        no_data = bool(item.get("no_data", False))
        replacement_raw = item.get("replacement")
        if no_data:
            if replacement_raw not in (None, ""):
                raise ValueError("标记无数据时replacement必须为空")
            replacement = None
        else:
            if replacement_raw in (None, ""):
                raise ValueError("未标记无数据时必须提供replacement")
            replacement = float(replacement_raw)
            if not 0 < replacement <= 100:
                raise ValueError("效率修订值必须在0~100之间")
        row, dim_index, level = _find_row(result, item)
        table_no = int(item["table_no"])
        power = float(item["power_kw"])
        key = (table_no, power, level, item["dimension"])
        if key in seen:
            raise ValueError(f"人工确认记录重复: {key}")
        seen.add(key)
        if int(item["pdf_page"]) not in next(t for t in result["tables"] if int(t["table_no"]) == table_no).get("pages", []):
            raise ValueError(f"表{table_no}的PDF页码不在标准包页码记录中")
        current = row["efficiency"][str(level)][dim_index]
        target_table = next(t for t in result["tables"] if int(t["table_no"]) == table_no)
        target_grades = row.get("efficiency", {})
        if isinstance(target_grades, dict) and len(target_grades) == 1:
            # 表8～表28的机器包只保存一个等级；该类表的存疑/无数据
            # 索引是该等级数组内的行内索引，而不是三等级展开索引。
            flat_index = dim_index
        else:
            flat_index = (level - 1) * len(target_table.get("dims", [])) + dim_index
        suspicious_indexes = [int(value) for value in row.get("suspicious_cells", [])]
        no_data_indexes = [int(value) for value in row.get("no_data_cells", [])]
        if flat_index not in suspicious_indexes and flat_index not in no_data_indexes:
            raise ValueError(f"目标单元格不是机器包登记的存疑/无数据单元格: {key}")
        if current not in (0.0, None):
            raise ValueError(f"目标单元格当前值不是存疑空值/0.0，拒绝覆盖: {key}")
        row["efficiency"][str(level)][dim_index] = replacement
        row["suspicious_cells"] = [value for value in row.get("suspicious_cells", []) if int(value) != flat_index]
        if not row["suspicious_cells"]:
            row.pop("suspicious_cells", None)
        if not no_data:
            # 修订了原先登记为无数据的单元格时才移除无数据标记；确认原文
            # 仍为“—”必须保留标记，否则激活后评价器无法区分“标准无数据”
            # 与损坏/缺失的数值。
            row["no_data_cells"] = [value for value in row.get("no_data_cells", []) if int(value) != flat_index]
            if not row["no_data_cells"]:
                row.pop("no_data_cells", None)
        applied.append({**item, "replacement": replacement, "no_data": no_data, "previous_value": current, "dimension_index": dim_index})

    if any(row.get("suspicious_cells") for table in result["tables"] for row in table.get("rows", [])):
        raise ValueError("仍有未确认的存疑单元格")
    result["status"] = "active"
    result["data_version"] = "pdf-rebuild-2026.08.23-user-reviewed-2026.08.30"
    # Do not carry the pre-activation gate message into an active package;
    # provenance and confirmed no-data semantics remain in activation_review
    # and row-level no_data_cells metadata.
    result.pop("unavailable_reason", None)
    result["verified_table_count"] = 29
    result["activation_review"] = {
        "reviewer": reviewer,
        "review_date": review_date,
        "all_cells_reviewed": True,
        "reviewed_tables": list(range(1, 30)),
        "reviewed_efficiency_cell_count": reviewed_cell_count,
        "reviewed_paths_sha256": _paths_digest(_expected_efficiency_paths(pack)),
        "pack_id": pack.get("pack_id"),
        "source_sha256": pack.get("source_sha256", ""),
        "items": applied,
        # 记录包内稳定引用而非激活机器上的绝对路径，便于wheel、pyz、
        # Linux和Android桥接复用；source_sha256仍绑定实际输入包内容。
        "source_pack": "resources/standards/gb30253_2024_pdf_verified_v1.json",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="人工确认后激活GB 30253-2024 PDF重建包")
    parser.add_argument("input", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = activate(args.input, args.review, args.output)
    print(json.dumps({"status": result["status"], "verified_table_count": result["verified_table_count"], "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
