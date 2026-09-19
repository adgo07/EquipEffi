"""十进制定点查表与插值工具。

标准明确允许插值时由设备评价器显式调用；本模块从不外推，也不自动取最近档。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable


def decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        raise ValueError("缺少数值")
    try:
        result = Decimal(str(value).strip())
        if not result.is_finite():
            raise ValueError(f"数值必须为有限数: {value!r}")
        return result
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"不是有效数值: {value!r}") from exc


def rounded(value: Decimal, digits: int = 6) -> Decimal:
    quantum = Decimal(1).scaleb(-digits)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def linear_interpolate(
    x: Any, x0: Any, y0: Any, x1: Any, y1: Any
) -> tuple[Decimal, Decimal]:
    x, x0, y0, x1, y1 = map(decimal, (x, x0, y0, x1, y1))
    if x1 == x0:
        raise ValueError("插值端点重合")
    if not min(x0, x1) <= x <= max(x0, x1):
        raise ValueError("禁止外推")
    factor = (x - x0) / (x1 - x0)
    return y0 + factor * (y1 - y0), factor


def bilinear_interpolate(
    x: Any,
    y: Any,
    x0: Any,
    x1: Any,
    y0: Any,
    y1: Any,
    q00: Any,
    q10: Any,
    q01: Any,
    q11: Any,
) -> tuple[Decimal, tuple[Decimal, Decimal]]:
    lower, fx = linear_interpolate(x, x0, q00, x1, q10)
    upper, _ = linear_interpolate(x, x0, q01, x1, q11)
    result, fy = linear_interpolate(y, y0, lower, y1, upper)
    return result, (fx, fy)


def bracket(rows: Iterable[dict[str, Any]], key: str, target: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    target_d = decimal(target)
    ordered = sorted(rows, key=lambda row: decimal(row[key]))
    for row in ordered:
        if decimal(row[key]) == target_d:
            return row, row
    lower = [row for row in ordered if decimal(row[key]) < target_d]
    upper = [row for row in ordered if decimal(row[key]) > target_d]
    if not lower or not upper:
        raise ValueError("目标值超出表格范围，禁止外推")
    return lower[-1], upper[0]
