"""GB 30253 evaluation for the five explicitly selected candidate branches."""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Mapping

from .input_contract import BRANCHES, COOLING_GROUPS, PmsmBranch
from .numeric import PROFILE_ID, PROFILE_VERSION, efficiency_display, exact_decimal, fraction_snapshot, frequency_evidence
from .pack import STANDARD_ID, Axis, Column, PmsmPack, PmsmPackError, Row, Table

CALCULATOR_VERSION = "gb30253-motor-pmsm-v1.0.0-candidate"
RULE_VERSION = "motor-pmsm-rule.v1"
ISSUE_001 = "EQP-STD-GB30253-001"
ISSUE_002 = "EQP-STD-GB30253-002"
ISSUE_003 = "EQP-STD-GB30253-003"
ISSUE_004 = "EQP-STD-GB30253-004"
_POWER_RANGE = {"A": (Fraction("0.55"), 1000), "B": (200, 2000),
                "C": (Fraction("0.55"), 1250), "D": (200, None), "E": (Fraction("0.55"), 110)}
_SPEED_RANGE = {"C": (45, 6000), "D": (45, 3000)}
_POLE_RANGE = {"A": (2, 16), "B": (4, 12)}


@dataclass(frozen=True)
class PmsmEvaluation:
    evaluation_status: str
    grade: str | None
    ui_conclusion: str
    reason_codes: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()
    thresholds: Mapping[str, Any] = field(default_factory=dict)
    references: Mapping[str, Any] = field(default_factory=dict)
    normalized_numbers: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _Selection:
    indices: tuple[int, ...]
    weight: Fraction = Fraction(0)
    provisional: bool = False

    @property
    def interpolated(self) -> bool:
        return len(self.indices) == 2


def _select_axis(value: Fraction, axes: tuple[Axis, ...], *, interval_lower: bool = False) -> _Selection | None:
    for index, axis in enumerate(axes):
        if axis.includes(value):
            return _Selection((index,))
    # A permitted power interval supplies only its inclusive lower endpoint,
    # and only while the other axis is fixed.
    points = sorted((axis.low, index) for index, axis in enumerate(axes)
                    if axis.is_point or interval_lower and axis.low is not None and axis.include_low)
    for (low, low_index), (high, high_index) in zip(points, points[1:]):
        if low < value < high:
            return _Selection((low_index, high_index), (value - low) / (high - low))
    return None


def _select_columns(table: Table, grade: int, dimension: Fraction, branch: PmsmBranch) -> _Selection | None:
    indices = tuple(index for index, column in enumerate(table.columns) if column.grade == grade)
    axes = tuple(table.columns[index].axis for index in indices)
    if branch.pole_axis:
        return next((_Selection((index,)) for index in indices
                     if table.columns[index].axis.includes(dimension)), None)
    if branch.code == "C" and 500 < dimension <= 600:
        low = next(index for index in indices if table.columns[index].axis.text == "500")
        high = next(index for index in indices if table.columns[index].axis.text == ">600～900")
        return _Selection((low, high), (dimension - 500) / 100, provisional=True)
    selected = _select_axis(dimension, axes)
    if selected is None:
        return None
    return _Selection(tuple(indices[index] for index in selected.indices), selected.weight)


def _source_cell(table: Table, row: Row, column: Column, index: int, pack: PmsmPack) -> dict[str, Any]:
    cell = f"{column.letter}{row.number}"
    issue = pack.excluded_cells.get(f"{table.sheet}!{cell}")
    text = row.efficiencies[index]
    return {
        "table_number": table.number, "source_sheet": table.sheet, "source_cell": cell,
        "source_text": text, "value_pct": None if issue or text == "—" else text,
        "power_cell": f"A{row.number}", "power_kw": row.power.text, "axis_cell": f"{column.letter}6",
        "axis": column.axis.text, "axis_unit": column.unit,
        "pdf_page": row.pdf_page, "printed_page": row.printed_page,
        "pdf_table_on_page": row.pdf_table_on_page, "pdf_row": row.pdf_row,
        **({"excluded_by_issue": issue} if issue else {}),
    }


def _interpolate(values: list[str | None], power: _Selection, speed: _Selection) -> Fraction | None:
    if any(value is None for value in values):
        return None
    weights_power = (1 - power.weight, power.weight) if power.interpolated else (Fraction(1),)
    weights_speed = (1 - speed.weight, speed.weight) if speed.interpolated else (Fraction(1),)
    weights = (left * right for left in weights_power for right in weights_speed)
    return sum((weight * exact_decimal(value) for weight, value in zip(weights, values, strict=True)), Fraction(0))


def _table_numbers(branch: PmsmBranch, voltage: Fraction, cooling: str | None) -> tuple[int, int, int]:
    if branch.code == "A":
        return (1, 1, 1)
    if branch.code == "C":
        return (8, 9, 10)
    if branch.code == "E":
        return (29, 29, 29)
    offset = next(index for index, codes in enumerate(COOLING_GROUPS) if cooling in codes)
    if branch.code == "B":
        number = 2 + offset + (3 if voltage == 10000 else 0)
        return (number, number, number)
    number = 11 + 3 * offset + (9 if voltage == 10000 else 0)
    return (number, number + 1, number + 2)


def _parse_inputs(values: Mapping[str, Any], branch: PmsmBranch):
    parsed = {}
    missing, invalid = [], []
    for field in branch.fields:
        if not field.required:
            continue
        key = field.field_id
        raw = values.get(key)
        if raw is None or isinstance(raw, str) and not raw.strip():
            missing.append(key)
            continue
        if key == "cooling_method":
            if not isinstance(raw, str) or len(raw) > 128:
                invalid.append(key)
            else:
                parsed[key] = raw.strip()
            continue
        try:
            exact = exact_decimal(raw)
            if exact <= 0 or key == "rated_efficiency_pct" and not 1 <= exact <= 100:
                raise ValueError("数值超出输入范围")
            if key == "poles" and exact.denominator != 1:
                raise ValueError("极数必须为整数")
            parsed[key] = exact
        except ValueError:
            if key == "rated_frequency_hz" and frequency_evidence(raw):
                parsed[key] = raw.strip()
            else:
                invalid.append(key)
    return parsed, tuple(missing), tuple(invalid)


class Gb30253MotorCalculator:
    calculator_version = CALCULATOR_VERSION
    numeric_profile_id = PROFILE_ID

    def evaluate(self, values: Mapping[str, Any], pack: PmsmPack, *,
                 numeric_profile_id: str = PROFILE_ID) -> PmsmEvaluation:
        if numeric_profile_id != PROFILE_ID:
            raise PmsmPackError("永磁电机Numeric Profile不匹配")
        refs = {
            "standard_id": STANDARD_ID, "numeric_contract_version": "v1",
            "numeric_profile_id": PROFILE_ID, "numeric_profile_version": PROFILE_VERSION,
            "calculator_version": CALCULATOR_VERSION, "rule_version": RULE_VERSION,
            "pack_sha256": pack.integrity_sha256,
            "standard_issues": {ISSUE_002: "RESOLVED", "EQP-STD-MOTOR-009": "RESOLVED"},
        }
        normalized = {}

        def result(status: str, reason: str, **kwargs: Any) -> PmsmEvaluation:
            label = {"INVALID_INPUT": "输入错误", "INSUFFICIENT_DATA": "无法判定",
                     "OUT_OF_STANDARD_SCOPE": "不在范围"}[status]
            return PmsmEvaluation(status, None, label, (reason,), references=refs,
                                  normalized_numbers=normalized, **kwargs)

        category = values.get("category_id")
        if category is None or isinstance(category, str) and not category.strip():
            return result("INSUFFICIENT_DATA", "MISSING_FIELD", missing_fields=("category_id",))
        if not isinstance(category, str) or category not in BRANCHES:
            return result("INVALID_INPUT", "CATEGORY_INVALID", invalid_fields=("category_id",))
        branch = BRANCHES[category]
        refs["branch"] = branch.code
        parsed, missing, invalid = _parse_inputs(values, branch)
        normalized.update({key: fraction_snapshot(value) for key, value in parsed.items()
                           if isinstance(value, Fraction)})
        if invalid:
            return result("INVALID_INPUT", "INPUT_INVALID", invalid_fields=invalid)
        if missing:
            return result("INSUFFICIENT_DATA", "MISSING_FIELD", missing_fields=missing)
        if branch.pole_axis and parsed["rated_frequency_hz"] != 50:
            return result("OUT_OF_STANDARD_SCOPE", "FREQUENCY_OUT_OF_SCOPE")
        voltage = parsed["rated_voltage_v"]
        if (branch.high_voltage and voltage not in (3000, 3300, 6000, 10000)
                or not branch.high_voltage and voltage > 1140):
            return result("OUT_OF_STANDARD_SCOPE", "VOLTAGE_OUT_OF_SCOPE")
        cooling = parsed.get("cooling_method")
        if branch.high_voltage and not any(cooling in codes for codes in COOLING_GROUPS):
            return result("OUT_OF_STANDARD_SCOPE", "COOLING_OUT_OF_SCOPE")

        numbers = _table_numbers(branch, voltage, cooling)
        refs["table_numbers"] = list(dict.fromkeys(numbers))
        refs["table_number"] = numbers[0]
        power = parsed["rated_output_power_kw"]
        minimum, maximum = _POWER_RANGE[branch.code]
        if power < minimum or maximum is not None and power > maximum:
            return result("OUT_OF_STANDARD_SCOPE", "POWER_OUT_OF_SCOPE")
        dimension = parsed["poles" if branch.pole_axis else "rated_speed_rpm"]
        axis_range = _POLE_RANGE.get(branch.code) if branch.pole_axis else _SPEED_RANGE.get(branch.code)
        if axis_range is not None and not axis_range[0] <= dimension <= axis_range[1]:
            reason = "POLES_OUT_OF_SCOPE" if branch.pole_axis else "SPEED_OUT_OF_SCOPE"
            return result("OUT_OF_STANDARD_SCOPE", reason)
        if branch.code == "A" and dimension == 12:
            refs["standard_issues"][ISSUE_001] = "RESOLVED"
            refs["effective_max_power_kw"] = "45"

        thresholds = {}
        exact = {}
        grade_lookups = {}
        refs["grade_lookups"] = grade_lookups
        for grade, number in enumerate(numbers, 1):
            table = pack.tables[number - 1]
            key = f"grade_{grade}"
            lookup = {"table_number": number}
            grade_lookups[key] = lookup
            columns = _select_columns(table, grade, dimension, branch)
            if columns is None:
                lookup["reason"] = "NO_POLE_COLUMN" if branch.pole_axis else "NO_SPEED_ENDPOINT"
                continue
            if columns.provisional:
                refs["standard_issues"][ISSUE_003] = "PROVISIONAL"
                lookup["speed_anchor"] = {"rated_speed_rpm": "600", "source_axis": ">600～900", "issue_id": ISSUE_003}
            rows = _select_axis(power, tuple(row.power for row in table.rows), interval_lower=not columns.interpolated)
            if rows is None:
                lookup["reason"] = "NO_POWER_ENDPOINT"
                continue
            cells = [_source_cell(table, table.rows[row], table.columns[column], column, pack)
                     for row in rows.indices for column in columns.indices]
            lookup["source_cells"] = cells
            if rows.interpolated and columns.interpolated:
                method = "BILINEAR_INTERPOLATION"
                if not columns.provisional:
                    refs["standard_issues"][ISSUE_004] = "RESOLVED"
            elif rows.interpolated or columns.interpolated:
                method = "LINEAR_INTERPOLATION"
            elif not table.rows[rows.indices[0]].power.is_point or not table.columns[columns.indices[0]].axis.is_point:
                method = "INTERVAL"
            else:
                method = "DIRECT"
            lookup.update(method=method, power_weight=fraction_snapshot(rows.weight),
                          speed_weight=fraction_snapshot(columns.weight))
            if rows.interpolated and not table.rows[rows.indices[-1]].power.is_point:
                lookup["power_interval_lower_endpoint_kw"] = str(table.rows[rows.indices[-1]].power.low)
            threshold = _interpolate([cell["value_pct"] for cell in cells], rows, columns)
            if threshold is None:
                lookup["reason"] = "NO_THRESHOLD"
                continue
            exact[grade] = threshold
            thresholds[key] = {
                "exact": fraction_snapshot(threshold) | {"unit": "percent_point"},
                "display": efficiency_display(threshold) if rows.interpolated or columns.interpolated
                else cells[0]["source_text"],
            }

        if len(exact) < 3:
            reasons = tuple(dict.fromkeys(lookup["reason"] for lookup in grade_lookups.values() if "reason" in lookup))
            return PmsmEvaluation("INSUFFICIENT_DATA", None, "无法判定", reasons,
                                  thresholds=thresholds, references=refs, normalized_numbers=normalized)
        efficiency = parsed["rated_efficiency_pct"]
        grade = next((str(level) for level, threshold in exact.items() if efficiency >= threshold), None)
        return PmsmEvaluation("SUCCESS", grade, f"{grade}级" if grade else "未达3级",
                              thresholds=thresholds, references=refs, normalized_numbers=normalized)
