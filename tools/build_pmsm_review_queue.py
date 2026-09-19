"""生成GB 30253-2024永磁同步电动机人工复核清单。

清单面向人工逐表/逐格核对，来源仅为本轮PDF重建包；不会修改机器标准数据，
也不会改变manifest中的``active``状态。
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs" / f"final_{date.today().strftime('%Y%m%d')}" / "GB30253-2024_PMSM人工复核清单.md"


def _cell_label(table: dict[str, Any], row: dict[str, Any], index: int) -> str:
    dimensions = table.get("dims") or []
    dimension = dimensions[index % len(dimensions)] if dimensions else "?"
    level = index // len(dimensions) + 1 if dimensions else "?"
    return f"{table.get('table', '')}｜{row.get('power_kw', row.get('power_rule', ''))} kW｜{level}级｜维度{dimension}"


def build_report(source: Path = DEFAULT_SOURCE) -> str:
    source = Path(source).resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    tables = list(payload.get("tables", []))
    suspicious: list[tuple[dict[str, Any], dict[str, Any], int]] = []
    for table in tables:
        for row in table.get("rows", []):
            for index in row.get("suspicious_cells", []) or []:
                suspicious.append((table, row, int(index)))
    status = str(payload.get("status", ""))
    status_note = "已完成用户复核；激活状态以manifest为准" if status == "active" else "复核完成前不得改为active"
    lines = [
        "# GB 30253-2024 永磁同步电动机人工复核清单",
        "",
        f"- 标准包：`{payload.get('pack_id', '')}`",
        f"- 标准状态：`{status}`（{status_note}）",
        f"- 原始PDF：`{payload.get('source_file', '')}`",
        f"- PDF SHA-256：`{payload.get('source_sha256', '')}`",
        f"- 结构化表数：{len(tables)}（manifest记录：{payload.get('verified_table_count', '')}）",
        f"- 生成日期：{date.today().isoformat()}",
        "",
        "## 复核方法",
        "",
        "1. 按下表逐项打开原始PDF对应页，核对表题、产品类别、电压/冷却条件、功率档、极数或转速区间、效率值和‘—’。",
        "2. 发现任何看不清或与结构化值不一致的单元格，标记为‘存疑’，不要根据单调趋势猜改。",
        "3. 只有29张表全部完成逐格复核，且人工校对册状态全部为‘正确’后，才允许进入active评估。",
        "",
        "## 表级清单",
        "",
        "| 序号 | 表号 | 产品 | 电压组 | 冷却组 | 维度方式 | 维度值 | PDF页码 | 数据行数 | 存疑单元格 | 已确认无数据 |",
        "|---:|---|---|---|---|---|---|---|---:|---:|---:|",
    ]
    for number, table in enumerate(tables, start=1):
        pages = ", ".join(str(item) for item in table.get("pages", []))
        dims = ", ".join(str(item) for item in table.get("dims", []))
        suspicious_count = sum(len(row.get("suspicious_cells", []) or []) for row in table.get("rows", []))
        no_data_count = sum(len(row.get("no_data_cells", []) or []) for row in table.get("rows", []))
        lines.append(
            f"| {number} | {table.get('table', '')} | {table.get('product', '')} | "
            f"{table.get('voltage_group', '')} | {table.get('cooling_group', '')} | "
            f"{table.get('mode', '')} | {dims} | {pages} | {len(table.get('rows', []))} | {suspicious_count} | {no_data_count} |"
        )
    lines.extend(["", "## 存疑单元格明细", ""])
    if suspicious:
        lines.extend([
            "| 表/位置 | PDF页码 | 当前结构化值 | 处理要求 |",
            "|---|---|---:|---|",
        ])
        for table, row, index in suspicious:
            pages = ", ".join(str(item) for item in table.get("pages", [])) or "待查"
            flat_values: list[Any] = []
            for level in ("1", "2", "3"):
                flat_values.extend((row.get("efficiency", {}).get(level) or []))
            value = flat_values[index] if index < len(flat_values) else "未知"
            if value is None:
                value = "无数据（按空值处理）"
            lines.append(f"| {_cell_label(table, row, index)} | {pages} | {value} | 保留原值，PDF逐格确认后再提出修订 |")
    else:
        lines.append("当前机器包未记录存疑单元格；仍须完成全部29张表人工核对。")
    confirmed_no_data = [
        (table, row, int(index))
        for table in tables
        for row in table.get("rows", [])
        for index in (row.get("no_data_cells", []) or [])
    ]
    lines.extend(["", "## 已确认无数据单元格", ""])
    if confirmed_no_data:
        lines.extend([
            "以下单元格按标准原文无数据处理，保留为空，不参与插值或等级比较；表1/55 kW/12极三档命中时按用户复核结果判定为‘不在范围’。",
            "",
            "| 表/位置 | PDF页码 | 处理 |",
            "|---|---|---|",
        ])
        for table, row, index in confirmed_no_data:
            pages = ", ".join(str(item) for item in table.get("pages", [])) or "待查"
            lines.append(f"| {_cell_label(table, row, index)} | {pages} | {row.get('no_data_reason', '无数据（按空值处理）')} |")
    else:
        lines.append("当前机器包未登记已确认无数据单元格。")
    lines.extend([
        "",
        "## 激活前检查",
        "",
        "- [ ] 29张表表题和适用条件均与PDF一致",
        "- [ ] 所有功率、极数/转速和效率单元格均已逐格确认",
        "- [ ] PDF中的‘—’未被转换为0或普通空值",
        "- [ ] 人工校对册所有记录状态为‘正确’",
        "- [ ] `gb30253_2024_pdf_verified_v1` 状态经复核后才允许升为 `active`",
        "",
    ])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成GB30253-2024 PMSM人工复核清单")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = build_report(args.source)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
