"""Phase 8B：离心泵批量评价**结果 Workbook** Writer（Excel-as-adapter）。

硬规则（Owner Phase 8 / 8B）
----------------------------
- 从原始输入 Workbook 创建**新文件**，**绝不**覆盖原输入文件。
- 默认文件名：``原文件名_评价结果_YYYYMMDD_HHMMSS.xlsx``。
- 目标文件已存在时**不得静默覆盖**（显式报错）。
- 只向「离心泵」Sheet 的**已有结果区域**写正式软件 Result；
  不删除、不重排其他 Sheet，不用 Writer 重做其他设备业务模板。
- 不新增另一套结果字段体系：列映射**复用 V6 现有列**。

列映射（复用 V6 既有结果列）
----------------------------
```text
N  比转速                      O/P/Q  C1 / C2 / C3
R  基准效率                    S  效率修正值
T  规定点效率                  U/V/W  1 / 2 / 3 级效率（= 关键限值）
X  能效等级 / 处理·评价状态     AA  自动备注 / 说明
```

V6 的「离心泵」Sheet 只有这 12 个结果列，没有独立的"处理状态"或"关键限值"列。
因此**复用** `X` 承载"处理/评价状态 + 最终结论 + 能效等级"，
复用 `U/V/W` 承载"关键限值"——而不是新增列体系。
逐行完整信息（原输入、数量、结论、等级、关键结果、问题说明）由
**原始输入列 + 这 12 个结果列**共同承载，结果 Workbook 因此是正式明细载体。

显示精度：写入**完整精度**数值，2 位小数显示由模板既有数字格式负责
（与 Phase 7 Qt 的显示约定一致，且等级比较仍使用完整精度）。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

from ...application.ports.batch_workbook import BatchRowOutcome
from .pump_workbook_reader import PUMP_SHEET

#: 结果列（Excel 列字母 → 语义）。顺序即写回顺序。
RESULT_FIELDS: tuple[tuple[str, str], ...] = (
    ("N", "specific_speed"),
    ("O", "c1"),
    ("P", "c2"),
    ("Q", "c3"),
    ("R", "base_efficiency"),
    ("S", "correction"),
    ("T", "specified_efficiency"),
    ("U", "grade1"),
    ("V", "grade2"),
    ("W", "grade3"),
    ("X", "conclusion"),
    ("AA", "auto_note"),
)

#: 派生量名称 → 结果列（`calculation_trace.derived` 的键为中文名）。
_DERIVED_BY_COLUMN: dict[str, str] = {
    "N": "比转速 ns",
    "O": "C1",
    "P": "C2",
    "Q": "C3",
    "R": "基准效率（%）",
    "S": "效率修正值（%）",
    "T": "规定点效率（%）",
    "U": "1级效率（%）",
    "V": "2级效率（%）",
    "W": "3级效率（%）",
}

#: 结果列中按数值写入的列（其余按文本）。
_NUMERIC_COLUMNS: frozenset[str] = frozenset("NOPQRSTUVW")

#: 结果文件默认名中缀。
RESULT_FILENAME_INFIX = "_评价结果_"


def default_result_filename(source: Path, when: datetime | None = None) -> str:
    """``原文件名_评价结果_YYYYMMDD_HHMMSS.xlsx``（Owner 8B 默认命名）。"""

    source = Path(source)
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{source.stem}{RESULT_FILENAME_INFIX}{stamp}.xlsx"


class ResultWorkbookExistsError(FileExistsError):
    """目标结果文件已存在；不得静默覆盖。"""


def _text_or_none(value: str) -> str | None:
    text = str(value or "").strip()
    return text or None


def _as_number(value: Any) -> Any:
    """转成 Excel 可写的数值；无法转换时退回原值（文本），绝不静默丢数据。"""

    from decimal import Decimal, InvalidOperation

    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return value
    if not number.is_finite():
        return value
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def _derived_value(derived: dict[str, Any], column: str) -> Any:
    name = _DERIVED_BY_COLUMN.get(column)
    if not name:
        return None
    if name in derived:
        return derived[name]
    # 派生量命名带单位后缀时做一次前缀匹配，避免因措辞差异漏写。
    prefix = name.split("（")[0]
    for key, value in derived.items():
        if str(key).strip().startswith(prefix):
            return value
    return None


def _status_and_conclusion(outcome: BatchRowOutcome) -> str:
    """`X` 列内容：处理 / 评价状态 + 最终结论 + 能效等级。

    输入错误与执行失败**不属于**正式评价结论，因此必须能一眼区分。
    """

    if outcome.is_input_error:
        return f"输入错误（{outcome.conclusion}）"
    if outcome.is_execution_error:
        return f"执行失败（{outcome.conclusion}）"
    if outcome.grade and str(outcome.grade) not in str(outcome.conclusion):
        return f"{outcome.conclusion}（{outcome.grade}级）"
    return outcome.conclusion


def _auto_note(outcome: BatchRowOutcome) -> str:
    return "；".join(dict.fromkeys(outcome.messages)) if outcome.messages else ""


class PumpResultWorkbookWriter:
    """把评价结果写入**新的**结果 Workbook。"""

    def default_destination(self, source: Path) -> Path:
        """``原文件名_评价结果_YYYYMMDD_HHMMSS.xlsx``（与源文件同目录）。"""

        source = Path(source)
        return source.with_name(default_result_filename(source))

    def write(self, source: Path, outcomes: dict[int, BatchRowOutcome],
              destination: Path, *, overwrite: bool = False) -> Path:
        source = Path(source)
        destination = Path(destination)
        if source.resolve() == destination.resolve():
            raise ValueError("结果工作簿不得覆盖原始输入文件")
        if destination.exists() and not overwrite:
            raise ResultWorkbookExistsError(
                f"结果工作簿已存在，不得静默覆盖：{destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)

        workbook = openpyxl.load_workbook(source, data_only=False)
        try:
            sheet = workbook[PUMP_SHEET]
            for row_number, outcome in outcomes.items():
                derived = outcome.derived
                for column, _name in RESULT_FIELDS:
                    cell = sheet[f"{column}{row_number}"]
                    if column == "X":
                        cell.value = _text_or_none(_status_and_conclusion(outcome))
                        continue
                    if column == "AA":
                        cell.value = _text_or_none(_auto_note(outcome))
                        continue
                    raw = _derived_value(derived, column)
                    if raw in (None, ""):
                        cell.value = None
                        continue
                    cell.value = (_as_number(raw) if column in _NUMERIC_COLUMNS
                                  else str(raw))
            workbook.save(destination)
        finally:
            workbook.close()
        return destination
