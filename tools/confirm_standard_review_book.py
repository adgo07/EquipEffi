"""根据用户确认生成“全部标准已校对”的人工校对册副本。

该工具只修改人工校对册的人工状态列，不修改任何机器标准JSON、原文值、
规范化值或公式。输出必须与输入使用不同路径，便于保留原始校对册。

校对册历史版本中可能使用“已校对”作为状态；这里把它作为兼容别名规范化
为契约规定的“正确”。“需修改”“存疑”或非空建议修订值不会被自动接受。
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import copy
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

try:
    from .build_human_review_book import FLAT_HEADERS
except ImportError:  # direct execution: python tools/confirm_standard_review_book.py
    from build_human_review_book import FLAT_HEADERS


REVIEW_SHEET = "标准数据平铺"
EXPLANATION_SHEET = "校对说明"
HISTORY_SHEET = "版本变更记录"
VALID_STATUSES = {"未校对", "正确", "需修改", "存疑"}
COMPATIBLE_STATUSES = {"已校对": "正确"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _header_map(sheet: Any) -> dict[str, int]:
    return {
        str(cell.value): index
        for index, cell in enumerate(sheet[3], start=1)
        if cell.value not in (None, "")
    }


def _copy_row_style(sheet: Any, source_row: int, target_row: int, max_column: int) -> None:
    """Copy the readable style/protection of a neighbouring history row."""

    for column in range(1, max_column + 1):
        source = sheet.cell(source_row, column)
        target = sheet.cell(target_row, column)
        if source.has_style:
            target._style = copy(source._style)
        if source.number_format:
            target.number_format = source.number_format
        if source.alignment:
            target.alignment = copy(source.alignment)
        if source.protection:
            target.protection = copy(source.protection)


def _append_review_note(workbook: Any, reviewer: str, review_date: str, converted: int) -> None:
    """Add a compact, human-readable workbook-level confirmation note."""

    if EXPLANATION_SHEET in workbook.sheetnames:
        sheet = workbook[EXPLANATION_SHEET]
        target_row = sheet.max_row + 1
        source_row = max(1, sheet.max_row)
        _copy_row_style(sheet, source_row, target_row, min(2, sheet.max_column))
        sheet.cell(target_row, 1).value = "最近复核"
        sheet.cell(target_row, 2).value = (
            f"{reviewer}于{review_date}确认全部标准数据已校对；"
            f"本次将{converted}条历史状态规范化为“正确”，未修改标准数值。"
        )

    if HISTORY_SHEET in workbook.sheetnames:
        sheet = workbook[HISTORY_SHEET]
        target_row = sheet.max_row + 1
        source_row = max(1, sheet.max_row)
        _copy_row_style(sheet, source_row, target_row, min(5, sheet.max_column))
        values = (
            review_date,
            "全量标准数据人工校对确认",
            "用户确认标准数据平铺记录已全部校对；状态按契约统一为正确",
            "允许校对册通过activation_ready门禁；不改变机器标准值",
            "verified/active-ready",
        )
        for column, value in enumerate(values, start=1):
            sheet.cell(target_row, column).value = value


def confirm(
    input_path: Path,
    output_path: Path,
    *,
    reviewer: str = "用户确认",
    review_date: str | None = None,
    confirmation_path: Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    if input_path == output_path:
        raise ValueError("输出文件必须与输入文件不同，禁止覆盖原始校对册")
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    reviewer = str(reviewer).strip()
    if not reviewer:
        raise ValueError("reviewer不能为空")
    review_date = str(review_date or date.today().isoformat()).strip()
    try:
        date.fromisoformat(review_date)
    except ValueError as exc:
        raise ValueError("review_date必须为YYYY-MM-DD") from exc

    workbook = load_workbook(input_path, read_only=False, data_only=False)
    try:
        if REVIEW_SHEET not in workbook.sheetnames:
            raise ValueError(f"缺少{REVIEW_SHEET}sheet")
        sheet = workbook[REVIEW_SHEET]
        headers = _header_map(sheet)
        missing_headers = [name for name in FLAT_HEADERS if name not in headers]
        if missing_headers:
            raise ValueError("标准数据平铺缺少字段: " + ", ".join(missing_headers))
        id_column = headers["数据ID"]
        status_column = headers["校对状态"]
        replacement_column = headers["建议修订值"]
        counts_before: Counter[str] = Counter()
        counts_after: Counter[str] = Counter()
        invalid: list[tuple[int, Any]] = []
        unresolved: list[tuple[int, str, Any]] = []
        suggestions: list[tuple[int, Any]] = []
        rows = 0
        converted = 0
        for row in sheet.iter_rows(min_row=4, max_col=len(FLAT_HEADERS)):
            identifier = row[id_column - 1].value
            if identifier in (None, ""):
                continue
            rows += 1
            row_number = row[0].row
            original_status = row[status_column - 1].value
            original_text = str(original_status) if original_status not in (None, "") else ""
            raw_status = original_text.strip()
            counts_before[raw_status] += 1
            status = COMPATIBLE_STATUSES.get(raw_status, raw_status)
            if status not in VALID_STATUSES:
                invalid.append((row_number, original_status))
                continue
            replacement = row[replacement_column - 1].value
            if replacement not in (None, ""):
                suggestions.append((row_number, replacement))
            if status in {"需修改", "存疑"}:
                unresolved.append((row_number, status, identifier))
            # 用户确认“全部已校对”后，未规范的历史状态才会进入这里；
            # 已有正确状态保留原意见和其他人工内容。
            if status == "未校对" or status != original_text:
                sheet.cell(row_number, status_column).value = "正确"
                converted += 1
                status = "正确"
            counts_after[status] += 1

        if invalid:
            sample = ", ".join(f"第{row}行={value!r}" for row, value in invalid[:5])
            raise ValueError(f"存在无法识别的校对状态（{sample}）")
        if unresolved:
            sample = ", ".join(f"第{row}行/{identifier}" for row, _status, identifier in unresolved[:5])
            raise ValueError(f"仍有“需修改”或“存疑”记录，不能按全部正确输出（{sample}）")
        if suggestions:
            sample = ", ".join(f"第{row}行" for row, _value in suggestions[:5])
            raise ValueError(f"存在建议修订值，必须先与原文核对后再确认（{sample}）")
        if rows == 0:
            raise ValueError("标准数据平铺没有可确认的数据行")

        _append_review_note(workbook, reviewer, review_date, converted)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(output_path)
    finally:
        workbook.close()

    result: dict[str, Any] = {
        "input": str(input_path),
        "output": str(output_path),
        "reviewer": reviewer,
        "review_date": review_date,
        "data_rows": rows,
        "converted_rows": converted,
        "status_counts_before": dict(counts_before),
        "status_counts_after": dict(counts_after),
        "input_sha256": _sha256(input_path),
        "output_sha256": _sha256(output_path),
        "machine_values_modified": False,
    }
    if confirmation_path is not None:
        confirmation_path = Path(confirmation_path).resolve()
        confirmation_path.parent.mkdir(parents=True, exist_ok=True)
        confirmation_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["confirmation"] = str(confirmation_path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按用户确认生成全量已校对人工校对册副本")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reviewer", default="用户确认")
    parser.add_argument("--review-date", default=None)
    parser.add_argument("--confirmation", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(confirm(
            args.input,
            args.output,
            reviewer=args.reviewer,
            review_date=args.review_date,
            confirmation_path=args.confirmation,
        ), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
