"""Exact GB 18613—2020 efficiency evaluation for the six mapped tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from math import gcd
import re
from typing import Any, Mapping

from .input_contract import MOTOR_CATEGORIES, MotorInputError, normalize_motor_input, speed_band_label

DECIMAL_PROFILE_ID = "EQUIPEFFI_MOTOR_EXACT_LINEAR_V1"
CALCULATOR_VERSION = "gb18613-motor-gb18613_2020-v2.0.0"
PACK_SCHEMA_VERSION = "equipeffi.motor-standard-pack.v1"
PACK_ID = "gb18613_2020_v2"
STANDARD_CODE = "GB 18613-2020"
_NUMERIC_FIELDS = ("rated_output_power_kw", "rated_voltage_kv", "rated_frequency_hz", "poles", "max_nameplate_speed_rpm", "measured_efficiency_pct")
_FIELD_LABELS = {"category_id": "设备类别", "rated_output_power_kw": "额定输出功率(kW)", "rated_voltage_kv": "额定电压(kV)", "rated_frequency_hz": "额定频率(Hz)", "poles": "极数", "max_nameplate_speed_rpm": "铭牌标称最高转速(r/min)", "measured_efficiency_pct": "实测效率(%)"}
_DECIMAL_PATTERN = re.compile(r"^(?P<sign>[+-]?)(?P<int>\d*)(?:\.(?P<frac>\d*))?(?:[eE](?P<exp>[+-]?\d+))?$")


class MotorPackError(RuntimeError):
    """The supplied GB 18613 runtime pack is missing or malformed."""


@dataclass(frozen=True)
class MotorEvaluation:
    evaluation_status: str
    grade: str | None
    ui_conclusion: str
    thresholds: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    explanation: str = ""
    missing_fields: tuple[str, ...] = ()
    trace: tuple[Mapping[str, Any], ...] = ()
    reason_codes: tuple[str, ...] = ()
    conclusion: str | None = None
    references: Mapping[str, Any] = field(default_factory=dict)
    invalid_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Scaled:
    coefficient: int
    scale: int

    @classmethod
    def parse(cls, value: Any, field_id: str) -> "_Scaled":
        if isinstance(value, bool) or isinstance(value, float):
            raise _ValueError(field_id, "必须填写十进制数值，不能使用二进制浮点值。")
        if not isinstance(value, (str, int, Decimal)):
            raise _ValueError(field_id, "必须填写十进制数值。")
        raw = str(value).strip()
        if not raw:
            raise _ValueError(field_id, "不能为空。")
        if len(raw) > 128:
            raise _ValueError(field_id, "数值文本超过128个字符。")
        match = _DECIMAL_PATTERN.fullmatch(raw)
        if not match or not (match.group("int") or match.group("frac")):
            raise _ValueError(field_id, "不是有效十进制数值。")
        try:
            exponent = int(match.group("exp") or "0")
        except ValueError as exc:
            raise _ValueError(field_id, "科学计数法指数无效。") from exc
        if abs(exponent) > 30:
            raise _ValueError(field_id, "科学计数法指数绝对值不能超过30。")
        int_part, frac_part = match.group("int") or "", match.group("frac") or ""
        digits = int_part + frac_part
        if len(digits) > 30:
            raise _ValueError(field_id, "有效数字文本不能超过30位。")
        coeff = int(digits or "0") * (-1 if match.group("sign") == "-" else 1)
        scale = len(frac_part) - exponent
        if scale < 0:
            coeff *= 10 ** (-scale)
            scale = 0
        while scale and coeff % 10 == 0:
            coeff //= 10
            scale -= 1
        return cls(coeff, scale)

    def fraction(self) -> tuple[int, int]:
        den = 10 ** self.scale
        common = gcd(abs(self.coefficient), den) or 1
        return self.coefficient // common, den // common

    def as_integer(self, field_id: str) -> int:
        q, r = divmod(abs(self.coefficient), 10 ** self.scale)
        if r:
            raise _ValueError(field_id, "必须填写整数。")
        return -q if self.coefficient < 0 else q

    def times_power_of_ten(self, exponent: int) -> "_Scaled":
        scale = self.scale - exponent
        return _Scaled(self.coefficient * (10 ** (-scale)), 0) if scale < 0 else _Scaled(self.coefficient, scale)

    def plain(self) -> str:
        sign, digits = ("-" if self.coefficient < 0 else ""), str(abs(self.coefficient))
        if not self.scale:
            return sign + digits
        digits = digits.rjust(self.scale + 1, "0")
        return sign + digits[:-self.scale] + "." + digits[-self.scale:]


class _ValueError(ValueError):
    def __init__(self, field_id: str, message: str):
        super().__init__(message)
        self.field_id = field_id


def _compare(a: _Scaled, b: _Scaled) -> int:
    scale = max(a.scale, b.scale)
    ai, bi = a.coefficient * 10 ** (scale - a.scale), b.coefficient * 10 ** (scale - b.scale)
    return (ai > bi) - (ai < bi)


def _ratio_dict(numerator: int, denominator: int) -> dict[str, str]:
    if denominator <= 0:
        raise MotorPackError("电机限值分母必须为正数。")
    divisor = gcd(abs(numerator), denominator) or 1
    return {"numerator": str(numerator // divisor), "denominator": str(denominator // divisor), "unit": "percent_point"}


def _round_half_up_two_places(n: int, d: int) -> str:
    if n < 0 or d <= 0:
        raise MotorPackError("电机阈值必须是非负有限分数。")
    q, r = divmod(100 * n, d)
    if 2 * r >= d:
        q += 1
    return f"{q // 100}.{q % 100:02d}"


def _empty_thresholds(reason: str | None = None) -> dict[str, dict[str, Any]]:
    return {f"grade_{level}": {"state": "NOT_COMPUTED", "exact": None, "display_text": None, "sources": [], "method": None, "reason": reason} for level in (1, 2, 3)}


def _field_label(field_id: str) -> str:
    return _FIELD_LABELS.get(field_id, field_id)


class Gb18613MotorCalculator:
    calculator_id = CALCULATOR_VERSION
    calculator_version = CALCULATOR_VERSION
    numeric_profile_id = DECIMAL_PROFILE_ID

    def evaluate(self, values: Mapping[str, Any], pack: Mapping[str, Any]) -> MotorEvaluation:
        try:
            normalized = normalize_motor_input(values)
        except MotorInputError as exc:
            return self._result("INVALID_INPUT", None, "输入错误", exc.message, reason_codes=("INPUT_INVALID",), invalid_fields=(exc.field,))
        category_id = normalized.get("category_id")
        if category_id is None:
            _, bad = self._parse_inputs(normalized, None)
            if bad:
                return self._invalid(bad)
            return self._result("INSUFFICIENT_DATA", None, "无法判定", "请选择明确的电动机类别。", missing_fields=("category_id",), reason_codes=("CATEGORY_MISSING",), conclusion="UNABLE_TO_JUDGE")
        if category_id in {"OTHER_CATEGORY", "UNCERTAIN_CATEGORY"}:
            _, bad = self._parse_inputs(normalized, None)
            if bad:
                return self._invalid(bad)
            if category_id == "OTHER_CATEGORY":
                return self._result("OUT_OF_STANDARD_SCOPE", None, "不在范围", "所选类别为“其他类别”，不进入GB 18613-2020六表评价。", thresholds=_empty_thresholds("OUT_OF_STANDARD_SCOPE"), reason_codes=("OUT_OF_SCOPE_EXPLICIT",), conclusion="OUT_OF_SCOPE")
            return self._result("INSUFFICIENT_DATA", None, "无法判定", "设备类别选择为“不确定类别”，不能据其他字段猜测适用表格。", thresholds=_empty_thresholds("CATEGORY_UNCERTAIN"), reason_codes=("CATEGORY_UNCERTAIN",), conclusion="UNABLE_TO_JUDGE")

        table_no = self._table_for_category(category_id)
        table = self._get_table(pack, table_no)
        references = self._references(pack, table)
        parsed, bad = self._parse_inputs(normalized, table_no)
        if bad:
            return self._invalid(bad, references)
        scope = self._scope_errors(table_no, parsed)
        if scope:
            labels = {"OUTSIDE_TABLE_POWER_RANGE": "额定输出功率超出类别表格范围", "RATED_VOLTAGE_OUT_OF_SCOPE": "额定电压超出类别适用范围", "RATED_FREQUENCY_OUT_OF_SCOPE": "额定频率不符合类别适用范围", "POLE_COUNT_OUT_OF_SCOPE": "极数不属于类别允许范围"}
            return self._result("OUT_OF_STANDARD_SCOPE", None, "不在范围", "；".join(labels[x] for x in scope) + "，不在GB 18613-2020相应评价范围。", thresholds=_empty_thresholds("OUT_OF_STANDARD_SCOPE"), reason_codes=tuple(scope), conclusion="OUT_OF_SCOPE", references=references)
        missing = tuple(field_id for field_id in self._required_route_fields(table_no) if parsed[field_id] is None)
        if missing:
            labels = "、".join(_field_label(x) for x in missing)
            return self._result("INSUFFICIENT_DATA", None, "无法判定", f"资料不足，请补充：{labels}。", thresholds=_empty_thresholds("MISSING_REQUIRED_INPUT"), missing_fields=missing, reason_codes=("MISSING_FIELD",), conclusion="UNABLE_TO_JUDGE", references=references)
        branch_id = self._branch_id(table_no, parsed)
        selected = self._select_thresholds(table, branch_id, parsed["rated_output_power_kw"])
        thresholds = selected["thresholds"]
        efficiency = parsed["measured_efficiency_pct"]
        trace = self._evaluation_trace(table, branch_id, selected, parsed, normalized, efficiency)
        if any(thresholds[f"grade_{n}"]["state"] != "AVAILABLE" for n in (1, 2, 3)):
            return self._result("INSUFFICIENT_DATA", None, "无法判定", "所选表格、极数/转速组或相邻功率端点存在无可用指标，不能跨缺值补算。", thresholds=thresholds, trace=(trace,), reason_codes=("NO_INDICATOR",), conclusion="UNABLE_TO_JUDGE", references=references)
        if efficiency is None:
            return self._result("INSUFFICIENT_DATA", None, "无法判定", "资料不足，请补充：实测效率(%)。", thresholds=thresholds, trace=(trace,), missing_fields=("measured_efficiency_pct",), reason_codes=("MISSING_FIELD",), conclusion="UNABLE_TO_JUDGE", references=references)
        basis = normalized["efficiency_basis_status"]
        reason = self._basis_block(basis)
        if reason:
            code, message = reason
            return self._result("INSUFFICIENT_DATA", None, "无法判定", message, thresholds=_empty_thresholds(code), reason_codes=(code,), conclusion="UNABLE_TO_JUDGE", references=references, trace=({"efficiency_basis_status": basis, "efficiency_basis_raw": normalized.get("efficiency_basis_raw", "")},))
        grade = self._classify(efficiency, thresholds)
        if grade is None:
            ui, conclusion, message = "未达3级", "NOT_COMPLIANT", "实测效率低于该表3级限值，未达到3级。"
        else:
            ui, conclusion, message = f"{grade}级", f"LEVEL_{grade}", f"实测效率达到该表{grade}级限值。"
        trace["comparison"] = {"measured_efficiency_pct": efficiency.plain(), "grade": grade, "policy": "FULL_VALUE_EXACT"}
        trace["grade"] = grade
        return self._result("SUCCESS", grade, ui, message, thresholds=thresholds, trace=(trace,), conclusion=conclusion, references=references)

    @staticmethod
    def _table_for_category(category_id: str) -> int:
        ids = {"three_phase_induction": 1, "capacitor_start": 2, "capacitor_run": 3, "two_value_capacitor": 4, "ac_fan_capacitor_run": 5, "ac_fan_brushless_dc": 6}
        try:
            return ids[category_id]
        except KeyError as exc:
            raise MotorPackError(f"未知电机类别路由: {category_id}") from exc

    @staticmethod
    def _required_route_fields(table_no: int) -> tuple[str, ...]:
        fields = ["rated_output_power_kw"]
        if table_no <= 4:
            fields.extend(("rated_voltage_kv", "rated_frequency_hz"))
        if table_no <= 5:
            fields.append("poles")
        if table_no == 6:
            fields.append("max_nameplate_speed_rpm")
        return tuple(fields)

    def _parse_inputs(self, values: Mapping[str, Any], table_no: int | None) -> tuple[dict[str, _Scaled | None], dict[str, str]]:
        out: dict[str, _Scaled | None] = {}
        errors: dict[str, str] = {}
        for field_id in _NUMERIC_FIELDS:
            raw = values.get(field_id)
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                out[field_id] = None
                continue
            try:
                out[field_id] = _Scaled.parse(raw, field_id)
            except _ValueError as exc:
                errors[field_id] = f"{_field_label(field_id)}{exc}"
        if errors:
            return out, errors
        active: set[str] = set()
        if table_no is not None:
            if table_no <= 4:
                active.update(("rated_voltage_kv", "rated_frequency_hz"))
            if table_no <= 5:
                active.add("poles")
            if table_no == 6:
                active.add("max_nameplate_speed_rpm")
        power, efficiency = out["rated_output_power_kw"], out["measured_efficiency_pct"]
        if power is not None and power.coefficient <= 0:
            errors["rated_output_power_kw"] = "额定输出功率必须大于0。"
        if efficiency is not None and (_compare(efficiency, _Scaled(1, 0)) < 0 or _compare(efficiency, _Scaled(100, 0)) > 0):
            errors["measured_efficiency_pct"] = "实测效率须为1%至100%的百分数点值。"
        for field_id in ("rated_voltage_kv", "rated_frequency_hz", "max_nameplate_speed_rpm"):
            value = out[field_id]
            if value is None:
                continue
            if field_id in active and value.coefficient <= 0:
                errors[field_id] = f"{_field_label(field_id)}必须大于0。"
            elif field_id not in active and value.coefficient < 0:
                errors[field_id] = f"不适用字段{_field_label(field_id)}留痕不得为负数。"
        poles = out["poles"]
        if poles is not None:
            try:
                number = poles.as_integer("poles")
                if "poles" in active and number <= 0:
                    errors["poles"] = "极数必须为正整数。"
                elif "poles" not in active and number < 0:
                    errors["poles"] = "不适用极数留痕不得为负数。"
            except _ValueError as exc:
                errors["poles"] = f"极数{exc}"
        return out, errors

    @staticmethod
    def _scope_errors(table_no: int, values: Mapping[str, _Scaled | None]) -> list[str]:
        category = next(item for item in MOTOR_CATEGORIES if item.table_no == table_no)
        facts = category.route_facts
        result: list[str] = []
        power = values.get("rated_output_power_kw")
        if power is not None and (_compare(power, _Scaled.parse(facts["power_min_kw"], "min")) < 0 or _compare(power, _Scaled.parse(facts["power_max_kw"], "max")) > 0):
            result.append("OUTSIDE_TABLE_POWER_RANGE")
        voltage, upper = values.get("rated_voltage_kv"), facts.get("rated_voltage_max_kv")
        if voltage is not None and upper is not None:
            cmp = _compare(voltage, _Scaled.parse(upper, "voltage max"))
            if cmp > 0 or (cmp == 0 and not facts.get("rated_voltage_max_inclusive", False)):
                result.append("RATED_VOLTAGE_OUT_OF_SCOPE")
        frequency, expected = values.get("rated_frequency_hz"), facts.get("rated_frequency_hz")
        if frequency is not None and expected is not None and _compare(frequency, _Scaled.parse(expected, "frequency")) != 0:
            result.append("RATED_FREQUENCY_OUT_OF_SCOPE")
        poles = values.get("poles")
        if poles is not None and facts.get("poles") and poles.as_integer("poles") not in facts["poles"]:
            result.append("POLE_COUNT_OUT_OF_SCOPE")
        return result

    @staticmethod
    def _basis_block(status: str) -> tuple[str, str] | None:
        return {
            "NAMEPLATE_ONLY": ("EFFICIENCY_BASIS_NAMEPLATE_ONLY", "仅有铭牌效率，不能替代规定工况下的实测效率。"),
            "KNOWN_NONCONFORMING": ("EFFICIENCY_BASIS_NONCONFORMING", "已知实测效率的试验工况不符合要求，不能据此判级。"),
            "UNKNOWN": ("EFFICIENCY_BASIS_UNKNOWN", "实测效率口径不确定，暂不能用于判级。"),
            "INSEPARABLE_MOTOR_ONLY": ("INSEPARABLE_MOTOR_ONLY", "表6驱动不可分离时须按电机与驱动整体效率评价；当前仅有电机本体效率。"),
        }.get(status)

    def _get_table(self, pack: Mapping[str, Any], table_no: int) -> Mapping[str, Any]:
        if not isinstance(pack, Mapping) or pack.get("schema_version") != "equipeffi.motor-standard-pack.v1" or pack.get("pack_id") != "gb18613_2020_v2":
            raise MotorPackError("GB 18613标准包schema或pack_id不匹配。")
        if pack.get("standard_code") != STANDARD_CODE or pack.get("numeric_profile_id") != DECIMAL_PROFILE_ID:
            raise MotorPackError("GB 18613标准包标准身份或Numeric Profile不匹配。")
        tables = pack.get("tables")
        if not isinstance(tables, list) or len(tables) != 6:
            raise MotorPackError("GB 18613标准包必须恰好包含表1至表6。")
        found = [x for x in tables if isinstance(x, Mapping) and x.get("table_no") == table_no]
        if len(found) != 1:
            raise MotorPackError(f"GB 18613标准包表{table_no}缺失或重复。")
        table = found[0]
        if table.get("table_id") != f"GB18613-T{table_no:02d}" or not isinstance(table.get("rows"), list) or table.get("branches") != self._expected_branches(table_no):
            raise MotorPackError(f"GB 18613标准包表{table_no}结构或分支无效。")
        return table

    @staticmethod
    def _expected_branches(table_no: int) -> list[dict[str, Any]]:
        allowed = {1: (2, 4, 6, 8), 2: (2, 4, 6), 3: (2, 4, 6), 4: (2, 4), 5: (4, 6, 8)}
        if table_no < 6:
            return [{"branch_id": f"poles_{p}", "dimension": "poles", "value": p} for p in allowed[table_no]]
        labels = ("r<=500", "500<r<=700", "700<r<=1000", "1000<r<=1300", "r>1300")
        return [{"branch_id": f"rpm_band_{i}", "dimension": "max_nameplate_speed_rpm", "value": label} for i, label in enumerate(labels, 1)]

    @staticmethod
    def _branch_id(table_no: int, values: Mapping[str, _Scaled | None]) -> str:
        if table_no < 6:
            return f"poles_{values['poles'].as_integer('poles')}"
        speed = values["max_nameplate_speed_rpm"]
        for band, limit in enumerate((500, 700, 1000, 1300), 1):
            if _compare(speed, _Scaled(limit, 0)) <= 0:
                return f"rpm_band_{band}"
        return "rpm_band_5"

    def _select_thresholds(self, table: Mapping[str, Any], branch_id: str, power_kw: _Scaled) -> dict[str, Any]:
        rows = []
        for row in table["rows"]:
            if not isinstance(row, Mapping) or not isinstance(row.get("power"), Mapping):
                raise MotorPackError("电机标准包存在无效功率行。")
            lower = _Scaled.parse(row["power"].get("normalized_w_lower"), "pack power lower")
            upper = _Scaled.parse(row["power"].get("normalized_w_upper"), "pack power upper")
            if _compare(lower, upper) > 0:
                raise MotorPackError("电机标准包功率区间倒置。")
            rows.append((lower, upper, row))
        power_w = power_kw.times_power_of_ten(3)
        direct = [(lo, hi, row) for lo, hi, row in rows if _compare(power_w, lo) >= 0 and _compare(power_w, hi) <= 0]
        if len(direct) > 1:
            raise MotorPackError("电机标准包功率区间重叠。")
        if direct:
            row = direct[0][2]
            return {"method": "DIRECT", "rows": [row], "power_w": power_w.plain(), "thresholds": {f"grade_{n}": self._direct_threshold(row, branch_id, n) for n in (1, 2, 3)}}
        table_no = table["table_no"]
        for row_index, ((left_lo, left_hi, left), (right_lo, right_hi, right)) in enumerate(zip(rows, rows[1:])):
            right_is_anchored_range = (
                table_no == 1 and row_index == len(rows) - 2
                and _compare(left_lo, _Scaled(250000, 0)) == 0
                and _compare(left_hi, _Scaled(250000, 0)) == 0
                and _compare(right_lo, _Scaled(315000, 0)) == 0
                and _compare(right_hi, _Scaled(1000000, 0)) == 0
            )
            if (_compare(left_lo, left_hi) == 0
                    and (_compare(right_lo, right_hi) == 0 or right_is_anchored_range)
                    and _compare(left_hi, power_w) < 0 and _compare(power_w, right_lo) < 0):
                return {"method": "LINEAR_INTERPOLATION", "rows": [left, right], "power_w": power_w.plain(),
                        "thresholds": {f"grade_{n}": self._interpolate(branch_id, n, left_hi, right_lo, power_w, left, right) for n in (1, 2, 3)}}
        raise MotorPackError("电机标准包没有覆盖该范围的相邻功率端点，不能外推或跨范围插值。")

    @staticmethod
    def _source_item(row: Mapping[str, Any], branch_id: str, level: int) -> Mapping[str, Any]:
        try:
            item = row["branches"][branch_id][f"grade_{level}"]
        except (KeyError, TypeError) as exc:
            raise MotorPackError(f"电机标准包缺少{branch_id}的{level}级源值。") from exc
        if not isinstance(item, Mapping) or item.get("state") not in {"AVAILABLE", "NO_INDICATOR"}:
            raise MotorPackError("电机标准包阈值状态无效。")
        if item["state"] == "AVAILABLE":
            _Scaled.parse(item.get("value"), "pack threshold")
            if not item.get("source_cell") or not item.get("source_row_id"):
                raise MotorPackError("电机标准包数值源缺少来源格或行ID。")
        elif item.get("source_state") not in {"HORIZONTAL_DASH", "SOURCE_BLANK"}:
            raise MotorPackError("电机标准包无指标状态缺少原始来源状态。")
        return item

    @staticmethod
    def _source_ref(item: Mapping[str, Any]) -> dict[str, Any]:
        return {"source_sheet": item.get("source_sheet"), "source_cell": item.get("source_cell"), "source_row_id": item.get("source_row_id"), "source_state": item.get("source_state"), "source_text": item.get("source_text", "")}

    def _direct_threshold(self, row: Mapping[str, Any], branch: str, level: int) -> dict[str, Any]:
        item = self._source_item(row, branch, level)
        if item["state"] == "NO_INDICATOR":
            return {"state": "NO_INDICATOR", "exact": None, "display_text": "—", "sources": [self._source_ref(item)], "method": "DIRECT", "reason": "SOURCE_HAS_NO_INDICATOR"}
        value = _Scaled.parse(item["value"], "threshold")
        n, d = value.fraction()
        return {"state": "AVAILABLE", "exact": _ratio_dict(n, d), "display_text": str(item.get("source_text") or value.plain()), "sources": [self._source_ref(item)], "method": "DIRECT", "reason": None}

    def _interpolate(self, branch: str, level: int, p0: _Scaled, p1: _Scaled, power: _Scaled, row0: Mapping[str, Any], row1: Mapping[str, Any]) -> dict[str, Any]:
        a, b = self._source_item(row0, branch, level), self._source_item(row1, branch, level)
        sources = [self._source_ref(a), self._source_ref(b)]
        if a["state"] != "AVAILABLE" or b["state"] != "AVAILABLE":
            return {"state": "NO_INDICATOR", "exact": None, "display_text": "—", "sources": sources, "method": "LINEAR_INTERPOLATION", "reason": "ADJACENT_ENDPOINT_HAS_NO_INDICATOR"}
        t0, t1 = _Scaled.parse(a["value"], "threshold"), _Scaled.parse(b["value"], "threshold")
        ps = max(p0.scale, p1.scale, power.scale)
        p0i, p1i, pi = p0.coefficient * 10 ** (ps-p0.scale), p1.coefficient * 10 ** (ps-p1.scale), power.coefficient * 10 ** (ps-power.scale)
        dp = p1i - p0i
        if dp <= 0 or not p0i < pi < p1i:
            raise MotorPackError("电机标准包插值端点不是递增的相邻区间。")
        ts = max(t0.scale, t1.scale)
        t0i, t1i = t0.coefficient * 10 ** (ts-t0.scale), t1.coefficient * 10 ** (ts-t1.scale)
        n, d = t0i * dp + (t1i-t0i) * (pi-p0i), dp * 10 ** ts
        reduced = _ratio_dict(n, d)
        n, d = int(reduced["numerator"]), int(reduced["denominator"])
        return {"state": "AVAILABLE", "exact": reduced, "display_text": _round_half_up_two_places(n, d), "sources": sources, "method": "LINEAR_INTERPOLATION", "reason": None}

    @staticmethod
    def _classify(efficiency: _Scaled, thresholds: Mapping[str, Mapping[str, Any]]) -> str | None:
        n, d = efficiency.fraction()
        for level in (1, 2, 3):
            exact = thresholds[f"grade_{level}"]["exact"]
            if n * int(exact["denominator"]) >= int(exact["numerator"]) * d:
                return str(level)
        return None

    def _evaluation_trace(self, table: Mapping[str, Any], branch: str, selected: Mapping[str, Any], parsed: Mapping[str, _Scaled | None], normalized: Mapping[str, Any], efficiency: _Scaled | None) -> dict[str, Any]:
        power = parsed["rated_output_power_kw"]
        source_rows = selected["rows"]
        endpoints = []
        for row in source_rows:
            p = row["power"]
            endpoints.append({"power_w": p["normalized_w_lower"], "source_power_text": p["source_text"], "source_unit": p["unit"], "source_row_id": row["source_row_id"]})
        sources = [{"grade": f"grade_{level}", **ref} for level in (1, 2, 3) for ref in selected["thresholds"][f"grade_{level}"]["sources"]]
        table_basis = table.get("required_test_basis", {})
        table_no = table["table_no"]
        return {"standard_code": STANDARD_CODE, "table_id": table["table_id"], "table_no": table_no,
                "source_sheet": table["source_sheet"], "branch_id": branch,
                "poles": parsed.get("poles").plain() if table_no <= 5 and parsed.get("poles") else None,
                "speed_band": branch if table_no == 6 else None,
                "speed_band_label": speed_band_label(branch) if table_no == 6 else None,
                "method": selected["method"], "rated_output_power_kw": power.plain() if power else None,
                "normalized_power_w": selected["power_w"], "power_endpoints": endpoints,
                "source_rows": [row["source_row_id"] for row in source_rows], "sources": sources,
                "thresholds": selected["thresholds"], "measured_efficiency_pct": efficiency.plain() if efficiency else None,
                "efficiency_basis_status": normalized.get("efficiency_basis_status"),
                "efficiency_basis_raw": normalized.get("efficiency_basis_raw", ""),
                "required_test_basis": table_basis, "comparison": None, "grade": None,
                "numeric_profile_id": DECIMAL_PROFILE_ID, "calculator_id": CALCULATOR_VERSION, "pack_id": PACK_ID}

    @staticmethod
    def _references(pack: Mapping[str, Any], table: Mapping[str, Any] | None = None) -> dict[str, Any]:
        result = {"standard_code": STANDARD_CODE, "pack_id": pack.get("pack_id", PACK_ID),
                  "data_version": pack.get("data_version"), "mapping_revision": pack.get("mapping_revision"),
                  "numeric_profile_id": DECIMAL_PROFILE_ID, "calculator_id": CALCULATOR_VERSION}
        if table is not None:
            result["required_test_basis"] = table.get("required_test_basis", {})
        return result

    def _result(self, status: str, grade: str | None, ui: str, message: str, *, thresholds: Mapping[str, Mapping[str, Any]] | None = None, missing_fields: tuple[str, ...] = (), trace: tuple[Mapping[str, Any], ...] = (), reason_codes: tuple[str, ...] = (), conclusion: str | None = None, invalid_fields: tuple[str, ...] = (), references: Mapping[str, Any] | None = None) -> MotorEvaluation:
        return MotorEvaluation(status, grade, ui, thresholds or _empty_thresholds(), message, missing_fields, trace, reason_codes, conclusion, references or {"standard_code": STANDARD_CODE, "pack_id": PACK_ID, "numeric_profile_id": DECIMAL_PROFILE_ID, "calculator_id": CALCULATOR_VERSION}, invalid_fields)

    def _invalid(self, errors: Mapping[str, str], references: Mapping[str, Any] | None = None) -> MotorEvaluation:
        return self._result("INVALID_INPUT", None, "输入错误", "；".join(errors.values()), reason_codes=("INPUT_INVALID",), invalid_fields=tuple(errors), references=references)


MotorCalculator = Gb18613MotorCalculator
