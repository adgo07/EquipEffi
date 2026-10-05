"""Phase 8B：离心泵批量评价**结果 Workbook** Writer（Excel-as-adapter）。

硬规则（Owner Phase 8 规则 12）
-------------------------------
- 输出必须是**新的** Workbook，**绝不**覆盖原始输入文件。
- 其他设备 Sheet 不得被删除、重排或改变业务内容。
- 「离心泵」Sheet 只**写入结果列**；用户输入列原样保留（含用户填的备注/图片）。

写入内容全部来自正式 Application 的评价结果：比转速 / C1~C3 / 基准效率 /
效率修正 / 规定点效率 / 1~3 级效率 / 能效等级 / 自动备注。
用户可见结论与 Qt 共用同一文案来源（`user_conclusion_text`），不得各写一套。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl

from ...application.services.centrifugal_pump_analysis_service import (
    user_conclusion_text,
)
from .pump_workbook_reader import PUMP_SHEET

#: 结果列（Excel 列字母 → 结果快照取值器）。
#:
#: 取值器接收（result 快照 dict, derived dict），返回要写进单元格的值。
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

#: 结果列允许写入的**数值型**列（其余按文本写入）。
_NUMERIC_COLUMNS: frozenset[str] = frozenset("NOPQRSTUVW")


@dataclass
class RowOutcome:
    """单行评价结果（写回与批次汇总的唯一来源）。"""

    row_number: int
    evaluated: bool
    conclusion: str
    evaluation_status: str | None
    grade: str | None
    messages: tuple[str, ...] = ()
    derived: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"row": self.row_number, "evaluated": self.evaluated,
                "conclusion": self.conclusion,
                "evaluation_status": self.evaluation_status,
                "grade": self.grade, "messages": list(self.messages)}


def outcome_from_result(row_number: int, result) -> RowOutcome:
    """把正式 Application 结果投影成可写回的行结果。"""

    snapshot = result.as_snapshot()
    derived = dict((result.calculation_trace or {}).get("derived") or {})
    messages: list[str] = []
    missing = snapshot.get("missing_fields") or []
    if missing:
        messages.append("缺少" + "、".join(str(item) for item in missing))
    explanation = str(snapshot.get("explanation") or "").strip()
    if explanation:
        messages.append(explanation)
    for warning in snapshot.get("warnings") or ():
        messages.append(str(warning))
    return RowOutcome(
        row_number=row_number,
        evaluated=bool(snapshot.get("evaluation_status")),
        conclusion=user_conclusion_text(result),
        evaluation_status=snapshot.get("evaluation_status"),
        grade=snapshot.get("grade"),
        messages=tuple(messages),
        derived=derived)


def _derived_value(derived: dict[str, Any], column: str) -> Any:
    name = _DERIVED_BY_COLUMN.get(column)
    if not name:
        return None
    if name in derived:
        return derived[name]
    # 派生量命名带单位后缀时做一次规范化匹配，避免因表头措辞差异漏写。
    for key, value in derived.items():
        if str(key).strip().startswith(name.split("（")[0]):
            return value
    return None


def _auto_note(outcome: RowOutcome) -> str:
    if not outcome.messages:
        return ""
    return "；".join(dict.fromkeys(outcome.messages))


class PumpResultWorkbookWriter:
    """把评价结果写入**新的**结果 Workbook。"""

    def write(self, source: Path, outcomes: dict[int, RowOutcome],
              destination: Path) -> Path:
        source = Path(source)
        destination = Path(destination)
        if source.resolve() == destination.resolve():
            raise ValueError("结果工作簿不得覆盖原始输入文件")
        destination.parent.mkdir(parents=True, exist_ok=True)

        workbook = openpyxl.load_workbook(source, data_only=False)
        try:
            sheet = workbook[PUMP_SHEET]
            for row_number, outcome in outcomes.items():
                derived = outcome.derived
                for column, _name in RESULT_FIELDS:
                    cell = sheet[f"{column}{row_number}"]
                    if column == "X":
                        cell.value = _text_or_none(outcome.conclusion)
                        continue
                    if column == "AA":
                        cell.value = _text_or_none(_auto_note(outcome))
                        continue
                    raw = _derived_value(derived, column)
                    if raw in (None, ""):
                        cell.value = None
                        continue
                    if column in _NUMERIC_COLUMNS:
                        # 写入**完整精度**数值，由模板既有的数字格式（如 `0.00`）
                        # 负责 2 位显示：证据不丢，显示仍然合规（Owner 规则 6）。
                        cell.value = _as_number(raw)
                    else:
                        cell.value = str(raw)
            workbook.save(destination)
        finally:
            workbook.close()
        return destination


def _text_or_none(value: str) -> str | None:
    text = str(value or "").strip()
    return text or None


def _as_number(value: Any) -> Any:
    """把结果值转成 Excel 可写的数值，**尽量保持十进制精度**。

    `Decimal` 直接交给 openpyxl 会以十进制字面量写入，是首选；
    无法转换时退回原值（文本），绝不静默丢数据。
    """

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
