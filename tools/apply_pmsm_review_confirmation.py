"""将用户对GB 30253-2024复核清单的确认写入校对册副本。

本工具不改写标准值、来源页码或其它标准包，只把指定标准编号在“标准数据
平铺”中的校对状态统一为“正确”。它用于记录用户已确认“除明确无数据单元
格外没有问题”的复核意见，输出必须是独立副本，不能覆盖输入校对册。
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path
from typing import Sequence

from openpyxl import load_workbook


STANDARD_CODE = "GB 30253-2024"


def confirm(input_path: Path, output_path: Path, *, reviewer: str, review_date: str) -> dict[str, object]:
    source = Path(input_path).resolve()
    target = Path(output_path).resolve()
    if source == target:
        raise ValueError("输出校对册必须与输入文件不同，禁止覆盖原始校对册")
    if not source.is_file():
        raise FileNotFoundError(source)
    reviewer = str(reviewer).strip()
    review_date = str(review_date).strip()
    if not reviewer:
        raise ValueError("reviewer不能为空")
    try:
        date.fromisoformat(review_date)
    except ValueError as exc:
        raise ValueError("review_date必须为YYYY-MM-DD") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    workbook = load_workbook(target, read_only=False, data_only=False)
    changed = 0
    total = 0
    no_data = 0
    try:
        if "标准数据平铺" not in workbook.sheetnames:
            raise ValueError("校对册缺少标准数据平铺sheet")
        sheet = workbook["标准数据平铺"]
        headers = {str(cell.value).strip(): cell.column for cell in sheet[3] if cell.value not in (None, "")}
        required = {"标准编号", "结构化区间", "规范化值", "校对状态", "校对意见"}
        missing = sorted(required - headers.keys())
        if missing:
            raise ValueError(f"标准数据平铺缺少列: {', '.join(missing)}")
        for row in range(4, sheet.max_row + 1):
            standard = str(sheet.cell(row, headers["标准编号"]).value or "").strip()
            if standard != STANDARD_CODE:
                continue
            total += 1
            status_cell = sheet.cell(row, headers["校对状态"])
            if str(status_cell.value or "").strip() != "正确":
                status_cell.value = "正确"
                changed += 1
            normalized = str(sheet.cell(row, headers["规范化值"]).value or "").strip()
            path = str(sheet.cell(row, headers["结构化区间"]).value or "").strip()
            if normalized == "—" and ".efficiency." in path:
                no_data += 1
                comment_cell = sheet.cell(row, headers["校对意见"])
                if not str(comment_cell.value or "").strip():
                    comment_cell.value = "用户已复核PDF原文：该单元格为‘—’，按无数据处理；命中时判定为不在范围"
        workbook.calculation.fullCalcOnLoad = True
        workbook.calculation.forceFullCalc = True
        workbook.calculation.calcMode = "auto"
        workbook.save(target)
    finally:
        workbook.close()
    return {
        "input": str(source),
        "output": str(target),
        "standard_code": STANDARD_CODE,
        "reviewer": reviewer,
        "review_date": review_date,
        "rows_confirmed": total,
        "rows_changed": changed,
        "confirmed_no_data_rows": no_data,
        "confirmation": "用户复核清单：表1中55 kW、12极的1级/2级/3级均为‘—’，其他内容未发现问题",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="记录用户对GB 30253-2024校对册的复核确认")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reviewer", default="用户确认")
    parser.add_argument("--review-date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    print(json.dumps(confirm(args.input, args.output, reviewer=args.reviewer, review_date=args.review_date), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
