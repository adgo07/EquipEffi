"""把GB 30253-2024机器数据包展开为便于人工核对的Markdown表格。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


def _cell(row: dict[str, Any], level: str, index: int) -> str:
    values = row.get("efficiency", {}).get(level, [])
    value = values[index] if index < len(values) else None
    markers = set(row.get("no_data_cells", []))
    # 1～3级表的机器包扁平索引按等级连续排列；单等级表索引从0开始。
    is_three_level = int(row.get("_table_no", 0)) <= 7 or int(row.get("_table_no", 0)) == 29
    try:
        flat_index = (int(level) - 1) * int(row["_dimension_count"]) + index if is_three_level else index
    except (KeyError, TypeError, ValueError):
        flat_index = index
    if flat_index in markers:
        return "—（无数据）"
    if value is None:
        return "—"
    if flat_index in set(row.get("suspicious_cells", [])):
        return f"{value}（存疑）"
    return str(value)


def _table_markdown(table: dict[str, Any]) -> list[str]:
    table_no = int(table.get("table_no", 0))
    dims = list(table.get("dims", []))
    three_level = table_no <= 7 or table_no == 29
    lines = [
        f"## {table.get('table', '表' + str(table_no))}",
        f"- 产品：{table.get('product', '')}",
        f"- 电压组：{table.get('voltage_group', '')}",
        f"- 冷却组：{table.get('cooling_group', '')}",
        f"- 维度：{table.get('mode', '')}；{', '.join(map(str, dims))}",
        f"- PDF页面：{', '.join(map(str, table.get('pages', [])))}",
        "",
    ]
    levels = ["1", "2", "3"] if three_level else [str(table.get("grade", ""))]
    for level in levels:
        title = f"### {level}级" if three_level else f"### 标准表值（{level}级）"
        lines.extend([title, "", "| 额定功率(kW) | " + " | ".join(map(str, dims)) + " |", "|---:|" + "---:|" * len(dims)])
        for original in table.get("rows", []):
            row = dict(original)
            row["_table_no"] = table_no
            row["_dimension_count"] = len(dims)
            power = row.get("power_rule", row.get("power_kw", ""))
            values = " | ".join(_cell(row, level, index) for index in range(len(dims)))
            lines.append(f"| {power} | {values} |")
        lines.append("")
    return lines


def export(pack_path: Path, output_path: Path) -> dict[str, Any]:
    payload = json.loads(Path(pack_path).read_text(encoding="utf-8"))
    if payload.get("standard_code") != "GB 30253-2024":
        raise ValueError("输入必须是GB 30253-2024永磁同步电动机标准包")
    tables = payload.get("tables")
    if not isinstance(tables, list) or len(tables) != 29:
        raise ValueError("标准包必须包含29张表")
    lines = [
        "# GB 30253-2024 永磁同步电动机标准数据可读备份",
        "",
        f"- 标准包：{payload.get('pack_id', '')}",
        f"- 状态：{payload.get('status', '')}（以manifest及人工复核记录为准）",
        f"- 数据版本：{payload.get('data_version', '')}",
        f"- 来源PDF：{payload.get('source_file', '')}",
        f"- PDF SHA-256：{payload.get('source_sha256', '')}",
        "",
        "本文件只读展示机器标准包，不替代原始PDF。‘—（无数据）’表示机器包登记的标准原文无数据，不能按0参与比较或插值；表1/55 kW/12极三档命中时按用户复核结果判定为‘不在范围’；‘存疑’表示需要人工回看PDF。",
        "",
    ]
    for table in tables:
        lines.extend(_table_markdown(table))
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "output": str(output_path),
        "table_count": len(tables),
        "line_count": len(lines),
        "status": payload.get("status", ""),
        "pack_id": payload.get("pack_id", ""),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导出PMSM标准数据Markdown可读备份")
    parser.add_argument("pack", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = export(args.pack, args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
