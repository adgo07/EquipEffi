"""将变压器计算追溯投影为面向用户的简短查表依据。"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
import re
from typing import Any


_TABLE_ID = re.compile(r"^GB20052-T(\d{2})$")
_SOURCE_SHEET = re.compile(r"^表\d{1,2}$")
_BRANCH_PART = re.compile(r"([a-z_]+)=([a-zA-Z0-9_.]+)")
_THERMAL_LABELS = {
    "B": "B级（100℃）",
    "F": "F级（120℃）",
    "H": "H级（145℃）",
}
_BRANCH_VALUE_LABELS = {
    ("core", "electrical_steel"): "电工钢铁心",
    ("core", "amorphous_alloy"): "非晶合金铁心",
    ("vector", "dyn11_yzn11"): "Dyn11/Yzn11",
    ("vector", "yyn0"): "Yyn0",
    ("uk_group", "A"): "额定阻抗A组",
    ("uk_group", "B"): "额定阻抗B组",
    ("uk_group", "C"): "额定阻抗C组",
    ("uk_group", "uk_4_0"): "4.0%阻抗组",
    ("uk_group", "uk_6_0_to_8_0"): "6.0%～8.0%阻抗组",
    ("loss_group", "ordinary"): "普通损耗",
    ("loss_group", "lv_66_69_special"): "66/69kV低压专用损耗",
}


def _decimal_text(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _table_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _TABLE_ID.fullmatch(value)
    return f"表{match.group(1)}" if match else None


def _branch_label(value: Any) -> str:
    if not isinstance(value, str) or "/" not in value:
        return ""
    suffix = value.split("/", 1)[1]
    labels: list[str] = []
    for key, raw in _BRANCH_PART.findall(suffix):
        label = _THERMAL_LABELS.get(raw) if key == "thermal" else None
        label = label or _BRANCH_VALUE_LABELS.get((key, raw))
        if label:
            labels.append(label)
    return "、".join(labels)


def _source_row(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        row = int(value)
        return row if row > 0 else None
    return None


def _source_labels(candidate: Mapping[str, Any]) -> list[str]:
    labels: list[tuple[str, int]] = []
    sources = candidate.get("sources")
    if not isinstance(sources, (tuple, list)):
        return []
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        sheet = source.get("source_sheet")
        row = _source_row(source.get("source_row"))
        if isinstance(sheet, str) and _SOURCE_SHEET.fullmatch(sheet) and row is not None:
            labels.append((sheet, row))

    # Keep each recorded source in order, including distinct rows from
    # same-value multi-branch matches. Grouping only shortens the display.
    grouped: dict[str, list[int]] = {}
    for sheet, row in labels:
        grouped.setdefault(sheet, []).append(row)
    return [f"{sheet}第{'、'.join(str(row) for row in rows)}行"
            for sheet, rows in grouped.items()]


def _candidate_line(candidate: Mapping[str, Any]) -> str | None:
    table = _table_label(candidate.get("table_id"))
    if table is None:
        # The localized source sheet is itself captured in the trace and can
        # identify the table when an older trace omitted table_id.
        sources = candidate.get("sources")
        if isinstance(sources, (tuple, list)):
            table = next((source.get("source_sheet") for source in sources
                          if isinstance(source, Mapping)
                          and isinstance(source.get("source_sheet"), str)
                          and _SOURCE_SHEET.fullmatch(source["source_sheet"])), None)

    branch = _branch_label(candidate.get("branch_id"))
    title = table or ""
    if branch:
        title = f"{title}，分支为{branch}" if title else f"分支为{branch}"

    lookup = candidate.get("lookup_method")
    capacity = _decimal_text(candidate.get("capacity_kva"))
    if lookup == "interpolated":
        lower = _decimal_text(candidate.get("lower_capacity_kva"))
        upper = _decimal_text(candidate.get("upper_capacity_kva"))
        detail = (f"额定容量{capacity} kVA按{lower}～{upper} kVA插值"
                  if capacity and lower and upper else "按容量插值")
    elif lookup == "exact":
        detail = f"按{capacity} kVA直接查表" if capacity else "直接查表"
    else:
        detail = ""

    sources = _source_labels(candidate)
    parts = [part for part in (title, detail) if part]
    if sources:
        parts.append("来源" + "、".join(sources))
    if not parts:
        return None
    return "查表依据：" + "；".join(parts) + "。"


def format_transformer_basis_lines(trace: Any) -> tuple[str, ...]:
    """只展示 trace 中实际保存的表、分支、插值端点与源行。

    内部标识、单元格坐标和原始 trace 均不进入用户文字。旧记录没有
    trace 或来源行时返回空结果，不从当前标准包推补历史依据。
    """

    if not isinstance(trace, (tuple, list)):
        return ()
    lines = [_candidate_line(candidate) for candidate in trace
             if isinstance(candidate, Mapping)]
    return tuple(line for line in lines if line)
