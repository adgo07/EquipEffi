"""Readable user-facing projection of GB 18613-2020 lookup traces."""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from ...domain.devices.motor.input_contract import speed_band_label


_TABLE_ID = re.compile(r"(?:GB18613-)?T0*(\d{1,2})$", re.IGNORECASE)
_TABLE_TEXT = re.compile(r"^表\s*0*(\d{1,2})$")
_CELL = re.compile(r"^[A-Z]{1,3}(\d+)$", re.IGNORECASE)


def _number(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _number_text(value: Any) -> str | None:
    number = _number(value)
    if number is None:
        return None
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _table_label(value: Any) -> str | None:
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 6:
        return f"表{value}"
    if not isinstance(value, str):
        return None
    value = value.strip()
    if match := _TABLE_TEXT.fullmatch(value):
        number = int(match.group(1))
        return f"表{number}" if 1 <= number <= 6 else None
    if match := _TABLE_ID.search(value):
        number = int(match.group(1))
        return f"表{number}" if 1 <= number <= 6 else None
    return None


def _row_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.isdigit():
        row = int(value)
        return row if row > 0 else None
    if match := _CELL.fullmatch(value):
        return int(match.group(1))
    return None


def _sources(trace: Mapping[str, Any]) -> list[str]:
    values = trace.get("sources", trace.get("source_rows", ()))
    if isinstance(values, Mapping):
        values = (values,)
    if not isinstance(values, (tuple, list)):
        return []
    grouped: dict[str, list[int]] = {}
    for source in values:
        if not isinstance(source, Mapping):
            continue
        table = _table_label(
            source.get("source_sheet", source.get("table_id", source.get("table_no"))))
        row = _row_number(source.get("source_row", source.get("row", source.get("source_cell"))))
        if table and row is not None:
            rows = grouped.setdefault(table, [])
            if row not in rows:
                rows.append(row)
    return [
        f"{table}第{'、'.join(str(row) for row in rows)}行"
        for table, rows in grouped.items()
    ]


def _source_power_kw(source: Mapping[str, Any]) -> str | None:
    unit = str(source.get("source_unit", "")).strip().lower()
    raw = source.get("source_power_text")
    if raw is None:
        raw = source.get("power_kw")
    value = _number(raw)
    if value is None and source.get("power_w") is not None:
        # A ranged source label such as "315~1000" is not one endpoint;
        # use the normalized watt anchor preserved beside it in the trace.
        value = _number(source.get("power_w"))
        unit = "w"
    if value is None:
        return None
    if unit in {"w", "watt", "watts", "瓦"}:
        value /= Decimal(1000)
    return _number_text(value)


def _endpoint_values(trace: Mapping[str, Any]) -> tuple[str | None, str | None]:
    endpoints = trace.get("power_endpoints", trace.get("endpoints"))
    if isinstance(endpoints, Mapping):
        low = endpoints.get("lower_kw", endpoints.get("lower", endpoints.get("low")))
        high = endpoints.get("upper_kw", endpoints.get("upper", endpoints.get("high")))
        return _number_text(low), _number_text(high)
    if isinstance(endpoints, (list, tuple)):
        powers = []
        for item in endpoints:
            if isinstance(item, Mapping):
                value = _source_power_kw(item)
            else:
                value = _number_text(item)
            if value is not None and value not in powers:
                powers.append(value)
        if powers:
            return powers[0], powers[-1]
    return (
        _number_text(trace.get("lower_power_kw")),
        _number_text(trace.get("upper_power_kw")),
    )


def _dimension_text(trace: Mapping[str, Any], table: str | None) -> str | None:
    poles = trace.get("poles", trace.get("pole_count"))
    if poles not in (None, ""):
        value = _number_text(poles)
        if value:
            return f"{value}极"

    band = trace.get("speed_band")
    speed = trace.get("max_nameplate_speed_rpm", trace.get("rated_speed_rpm"))
    if isinstance(band, Mapping):
        lower = _number_text(band.get("lower_rpm", band.get("min_rpm")))
        upper = _number_text(band.get("upper_rpm", band.get("max_rpm")))
        lower_open = band.get("lower_inclusive") is False
        upper_open = band.get("upper_inclusive") is False
        if lower is not None and upper is not None:
            interval = f"{'<' if lower_open else '≤'}{lower}～{upper}{'<' if upper_open else '≤'}"
        elif lower is not None:
            interval = f"{'>' if lower_open else '≥'}{lower}"
        elif upper is not None:
            interval = f"{'<' if upper_open else '≤'}{upper}"
        else:
            interval = ""
        if interval:
            return f"最高转速档{interval} r/min"
    if band not in (None, ""):
        label = trace.get("speed_band_label") or speed_band_label(str(band))
        if label:
            return f"最高转速档{label}"
        if "<" in str(band) or "≤" in str(band) or ">" in str(band):
            return f"最高转速档{str(band)} r/min"
    if speed not in (None, ""):
        value = _number_text(speed)
        if value:
            return f"铭牌最高转速{value} r/min"
    if table == "表6":
        return None
    return None


def _line(trace: Mapping[str, Any]) -> str | None:
    table = _table_label(trace.get("table_id", trace.get("table_no", trace.get("table"))))
    if table is None:
        sources = trace.get("sources", trace.get("source_rows", ()))
        if isinstance(sources, Mapping):
            sources = (sources,)
        if isinstance(sources, (tuple, list)):
            for source in sources:
                if isinstance(source, Mapping):
                    table = _table_label(source.get("source_sheet", source.get("table_id")))
                    if table:
                        break

    method = str(trace.get("method", trace.get("lookup_method", ""))).upper()
    if method in {"DIRECT", "EXACT", "EXACT_LOOKUP"}:
        detail = "直接查表"
    elif method in {"LINEAR_INTERPOLATION", "INTERPOLATED", "INTERPOLATION"}:
        detail = "线性插值"
    else:
        detail = ""

    power = _number_text(trace.get("rated_output_power_kw", trace.get("power_kw")))
    if detail == "直接查表":
        detail = f"额定功率{power} kW直接查表" if power else detail
    elif detail == "线性插值":
        low, high = _endpoint_values(trace)
        if power and low and high:
            detail = f"额定功率{power} kW按{low}～{high} kW线性插值"
        elif low and high:
            detail = f"按{low}～{high} kW线性插值"
        else:
            detail = "按功率线性插值"

    dimension = _dimension_text(trace, table)
    parts = [part for part in (table, dimension, detail) if part]
    sources = _sources(trace)
    if sources:
        parts.append("来源" + "、".join(sources))
    if not parts:
        return None
    return "查表依据：" + "；".join(parts) + "。"


def format_motor_basis_lines(trace: Any) -> tuple[str, ...]:
    """Format only table, branch dimension, interpolation and source facts.

    Internal IDs, cell coordinates, profile details, and current-pack-derived
    guesses are omitted. Missing legacy trace remains missing.
    """
    if isinstance(trace, Mapping):
        candidates = trace.get("steps")
        if candidates is None:
            candidates = trace.get("lookups")
        if not isinstance(candidates, (tuple, list)) or not candidates:
            candidates = (trace,)
    elif isinstance(trace, (tuple, list)):
        candidates = trace
    else:
        return ()
    lines: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        line = _line(candidate)
        if line and line not in lines:
            lines.append(line)
    return tuple(lines)
