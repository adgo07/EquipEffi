"""Phase 8 容量策略实测：少量 / 100 / 1,000 / 10,000 行的真实代价。

测量内容（都是**实测**，不预设阈值）：
- 生成后文件大小
- `ooxml_reader` 读取耗时与峰值内存
- 读取到的数据行数（**不得截断**）

用法::

    python tools/measure_v6_capacity.py --json artifacts/p8/capacity.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

TEMPLATE = (REPO_ROOT / "src" / "equipeffi" / "resources" / "templates"
            / "设备能效分析空白模板_重构版V6_20261005.xlsx")
PUMP_SHEET = "离心泵"
FIRST_DATA_ROW = 4
SCENARIOS: tuple[int, ...] = (3, 100, 1000, 10000)

CATEGORY_CYCLE = ("单级单吸清水离心泵", "单级双吸清水离心泵", "管道清水离心泵",
                  "多级清水离心泵", "轻型多级清水离心泵（立式）",
                  "轻型多级清水离心泵（卧式）", "单级石油化工离心泵",
                  "多级石油化工离心泵", "其他类别", "不确定类别")
SUCTION_CYCLE = ("单吸", "双吸")


@dataclass
class Scenario:
    rows: int
    file_size_bytes: int = 0
    read_seconds: float = 0.0
    peak_memory_bytes: int = 0
    rows_read: int = 0
    truncated: bool = False
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"rows_written": self.rows,
                "file_size_bytes": self.file_size_bytes,
                "read_seconds": round(self.read_seconds, 4),
                "peak_memory_bytes": self.peak_memory_bytes,
                "rows_read": self.rows_read,
                "truncated": self.truncated,
                "notes": self.notes}


def _fill(workbook, rows: int) -> None:
    sheet = workbook[PUMP_SHEET]
    for index in range(rows):
        row = FIRST_DATA_ROW + index
        sheet[f"A{row}"] = index + 1
        sheet[f"B{row}"] = f"设备{index + 1}"
        sheet[f"C{row}"] = f"M-{index + 1:05d}"
        sheet[f"D{row}"] = (index % 5) + 1
        sheet[f"E{row}"] = "1号车间"
        sheet[f"F{row}"] = CATEGORY_CYCLE[index % len(CATEGORY_CYCLE)]
        sheet[f"G{row}"] = 100 + index
        sheet[f"H{row}"] = 30 + (index % 20)
        sheet[f"I{row}"] = 2900
        sheet[f"J{row}"] = 45 + (index % 30)
        sheet[f"K{row}"] = SUCTION_CYCLE[index % 2]
        sheet[f"L{row}"] = 1 if "单级" in CATEGORY_CYCLE[index % len(CATEGORY_CYCLE)] else 2
        sheet[f"M{row}"] = 75 + (index % 15)


def measure(rows: int, workdir: Path) -> Scenario:
    from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook

    scenario = Scenario(rows=rows)
    target = workdir / f"pump_{rows}.xlsx"
    workbook = openpyxl.load_workbook(TEMPLATE, data_only=False)
    _fill(workbook, rows)
    workbook.save(target)
    scenario.file_size_bytes = target.stat().st_size

    # 冷读（不预热），测量真实读取代价。
    tracemalloc.start()
    start = time.perf_counter()
    with OOXMLWorkbook(target) as book:
        grid = book.rows(PUMP_SHEET)
    scenario.read_seconds = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    scenario.peak_memory_bytes = peak

    data_rows = [row for row in grid[FIRST_DATA_ROW - 1:] if any(
        str(cell).strip() for cell in row)]
    scenario.rows_read = len(data_rows)
    scenario.truncated = scenario.rows_read < rows

    # 关键行内容保真：首行 / 末行都必须读到。
    if data_rows:
        scenario.notes.append(f"first_A={data_rows[0][0]!r}")
        scenario.notes.append(f"last_A={data_rows[-1][0]!r}")
    target.unlink(missing_ok=True)
    return scenario


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--rows", type=int, nargs="*", default=list(SCENARIOS))
    args = parser.parse_args(argv)

    workdir = Path(tempfile.mkdtemp(prefix="p8-capacity-"))
    results: list[Scenario] = []
    try:
        for rows in args.rows:
            scenario = measure(rows, workdir)
            results.append(scenario)
            print(f"  rows={rows:<6} size={scenario.file_size_bytes/1024:>9.1f} KB "
                  f"read={scenario.read_seconds:>7.3f}s "
                  f"peak={scenario.peak_memory_bytes/1024/1024:>7.1f} MB "
                  f"read_rows={scenario.rows_read:<6} "
                  f"truncated={scenario.truncated}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    payload = {"template": str(TEMPLATE),
               "scenarios": [s.as_dict() for s in results],
               "any_truncated": any(s.truncated for s in results)}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    print()
    print("GATE: " + ("PASS" if not payload["any_truncated"] else "FAIL"))
    return 0 if not payload["any_truncated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
