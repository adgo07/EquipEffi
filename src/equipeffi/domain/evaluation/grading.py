from __future__ import annotations

from typing import Any, Iterable

from ..common.enums import ComparisonDirection, Conclusion
from .decimal_math import decimal


def compare(actual: Any, threshold: Any, direction: ComparisonDirection) -> bool:
    left, right = decimal(actual), decimal(threshold)
    if direction is ComparisonDirection.GREATER_OR_EQUAL:
        return left >= right
    return left <= right


def grade_three(
    actual: Any,
    thresholds: Iterable[Any],
    direction: ComparisonDirection,
) -> tuple[Conclusion, list[dict[str, Any]]]:
    values = list(thresholds)
    if len(values) != 3:
        raise ValueError("三级指标必须恰好包含1、2、3级三个值")
    trace: list[dict[str, Any]] = []
    selected: Conclusion | None = None
    for level, threshold in zip(
        (Conclusion.LEVEL_1, Conclusion.LEVEL_2, Conclusion.LEVEL_3), values
    ):
        passed = compare(actual, threshold, direction)
        trace.append(
            {
                "level": level.value,
                "actual": str(decimal(actual)),
                "direction": direction.value,
                "threshold": str(decimal(threshold)),
                "passed": passed,
            }
        )
        if passed and selected is None:
            selected = level
    return selected or Conclusion.NOT_COMPLIANT, trace


def grade_three_optional(
    actual: Any,
    thresholds: Iterable[Any],
    direction: ComparisonDirection,
    marker: str = "—",
) -> tuple[Conclusion, list[dict[str, Any]]]:
    """比较三级指标，同时保留标准表中“不作要求”的等级。

    标准表的破折号不是零值，也不是输入缺失。对应阈值使用 ``None``，
    该等级输出 ``applicable=False``，不参与等级选择；其余等级仍按
    通常的1→2→3顺序比较。用于存在部分等级空档的标准表。
    """
    values = list(thresholds)
    if len(values) != 3:
        raise ValueError("三级指标必须恰好包含1、2、3级三个值")
    trace: list[dict[str, Any]] = []
    selected: Conclusion | None = None
    for level, threshold in zip(
        (Conclusion.LEVEL_1, Conclusion.LEVEL_2, Conclusion.LEVEL_3), values
    ):
        if threshold is None:
            trace.append(
                {
                    "level": level.value,
                    "actual": str(decimal(actual)),
                    "direction": direction.value,
                    "threshold": None,
                    "passed": None,
                    "applicable": False,
                    "standard_marker": marker,
                }
            )
            continue
        passed = compare(actual, threshold, direction)
        trace.append(
            {
                "level": level.value,
                "actual": str(decimal(actual)),
                "direction": direction.value,
                "threshold": str(decimal(threshold)),
                "passed": passed,
                "applicable": True,
            }
        )
        if passed and selected is None:
            selected = level
    return selected or Conclusion.NOT_COMPLIANT, trace


def grade_five(actual: Any, thresholds: Iterable[Any]) -> tuple[Conclusion, list[dict[str, Any]]]:
    values = list(thresholds)
    if len(values) != 5:
        raise ValueError("五级指标必须恰好包含五个值")
    trace: list[dict[str, Any]] = []
    levels = (
        Conclusion.LEVEL_1,
        Conclusion.LEVEL_2,
        Conclusion.LEVEL_3,
        Conclusion.LEVEL_4,
        Conclusion.LEVEL_5,
    )
    selected: Conclusion | None = None
    for level, threshold in zip(levels, values):
        passed = compare(actual, threshold, ComparisonDirection.GREATER_OR_EQUAL)
        trace.append(
            {
                "level": level.value,
                "actual": str(decimal(actual)),
                "direction": ">=",
                "threshold": str(decimal(threshold)),
                "passed": passed,
            }
        )
        if passed and selected is None:
            selected = level
    return selected or Conclusion.NOT_COMPLIANT, trace
