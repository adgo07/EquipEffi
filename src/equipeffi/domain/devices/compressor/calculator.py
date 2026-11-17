"""GB19153六表精确查表；纯Domain，不依赖Excel或UI。"""
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from typing import Any, Mapping
import json
import re
from .input_contract import CATEGORIES, CONTRACT, REVISION
PROFILE_ID = "EQUIPEFFI_COMPRESSOR_EXACT_LOOKUP_V1"
CALCULATOR_VERSION = "gb19153-compressor-v1.0.0-candidate"
LEXEME = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class CompressorPackError(RuntimeError):
    """系统资源错误，不是业务资料不足。"""


def exact_decimal(value, *, numeric_profile_id):
    if numeric_profile_id != PROFILE_ID:
        raise CompressorPackError("空压机Numeric Profile不匹配")
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("须为精确十进制，拒绝float")
    if isinstance(value, int) and value.bit_length() > 100:
        raise ValueError("整数超过输入上限")
    text = str(value).strip()
    if len(text) > 128 or not LEXEME.fullmatch(text):
        raise ValueError("十进制格式无效")
    mantissa, _, exponent = text.lower().partition("e")
    if len(re.sub(r"[^0-9]", "", mantissa)
           ) > 30 or abs(int(exponent or "0")) > 30:
        raise ValueError("数值超过输入上限")
    return Fraction(text)


@dataclass(frozen=True)
class CompressorEvaluation:
    evaluation_status: str
    grade: str | None
    ui_conclusion: str
    reason_codes: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()
    thresholds: Mapping[str, Any] = field(default_factory=dict)
    references: Mapping[str, Any] = field(default_factory=dict)


class Gb19153CompressorCalculator:
    def __init__(self):
        self._indexes = {}

    calculator_version = CALCULATOR_VERSION
    numeric_profile_id = PROFILE_ID

    @staticmethod
    def validate_pack(pack):
        try:
            body = {k: v for k, v in pack.items() if k != "integrity_sha256"}
            digest = sha256(
                json.dumps(
                    body,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(
                        ",",
                        ":")).encode()).hexdigest()
            if pack["integrity_sha256"] != digest or pack["numeric_profile_id"] != PROFILE_ID or pack["standard_id"] != "GB19153-2019":
                raise ValueError("身份不符")
            if [t["table_number"]
                    for t in pack["tables"]] != list(range(1, 7)):
                raise ValueError("缺表")
        except (KeyError, TypeError, ValueError) as e:
            raise CompressorPackError("空压机标准包无效") from e

    def evaluate(self, values, pack, *, numeric_profile_id=PROFILE_ID):
        def parse(value): return exact_decimal(
            value, numeric_profile_id=numeric_profile_id)
        parse("1")
        self.validate_pack(pack)
        refs = dict(standard_id="GB19153-2019", numeric_contract_version="v1", numeric_profile_id=numeric_profile_id,
                    calculator_version=CALCULATOR_VERSION, rule_version="compressor-grade-rule.v1", pack_sha256=pack["integrity_sha256"],
                    assessment_scope="SPECIFIC_POWER_GRADE_ONLY", standard_issues=[f"EQP-STD-GB19153-{i:03}" for i in range(1, 6)])

        refs["numeric_profile_version"] = "1.0.0"
        refs["standard_issue_statuses"] = {
            f"EQP-STD-GB19153-{number:03}": "PROVISIONAL" if number <= 3 else "RESOLVED"
            for number in range(1, 6)
        }

        def result(status, reason, **kw):
            return CompressorEvaluation(status, None, {"INVALID_INPUT": "输入错误", "OUT_OF_STANDARD_SCOPE": "不在范围", "INSUFFICIENT_DATA": "无法判定"}[status],
                                        reason_codes=(reason,), references=refs, **kw)
        category = values.get("category_id")
        selected = next(
            (c for c in CATEGORIES if c.category_id == category), None)
        if selected is None:
            return result("INVALID_INPUT", "CATEGORY_INVALID",
                          invalid_fields=("category_id",))
        if values.get("input_contract_revision") not in (None, "", REVISION):
            return result("INVALID_INPUT", "CONTRACT_INVALID",
                          invalid_fields=("input_contract_revision",))
        if category == "OTHER_CATEGORY":
            return result("OUT_OF_STANDARD_SCOPE", "OTHER_CATEGORY")
        if category == "UNCERTAIN_CATEGORY":
            return result("INSUFFICIENT_DATA", "CATEGORY_UNCERTAIN")
        number = selected.table_no
        fields = CONTRACT.visible_fields(category)
        missing = []
        invalid = []
        nums = {}
        for f in fields:
            raw = values.get(f.field_id)
            if raw in (None, ""):
                if f.required:
                    missing.append(f.field_id)
                continue
            if f.field_id == "cooling_method":
                if raw not in ("AIR", "LIQUID"):
                    invalid.append(f.field_id)
            elif f.unit:
                try:
                    nums[f.field_id] = parse(raw)
                    if nums[f.field_id] <= 0:
                        invalid.append(f.field_id)
                except ValueError:
                    invalid.append(f.field_id)
        power_key = "rated_input_power_kw" if number >= 5 else "rated_motor_output_power_kw"
        forbidden = (
            "rated_motor_output_power_kw" if number >= 5 else "rated_input_power_kw",
            "input_power",
            "input_power_kw")
        for key in forbidden:
            if values.get(key) not in (None, ""):
                invalid.append(key)
        if number >= 5 and values.get("cooling_method") not in (None, ""):
            invalid.append("cooling_method")
        if missing or invalid:
            return result("INVALID_INPUT", "INPUT_INVALID", missing_fields=tuple(
                missing), invalid_fields=tuple(invalid))
        power, pressure = nums[power_key], nums["rated_discharge_pressure_mpa"]
        identity = pack["integrity_sha256"]
        if identity not in self._indexes:
            index = {}
            for table in pack["tables"]:
                rows = table["rows"]
                axis_power = sorted({parse(x["power_kw"]) for x in rows})
                axis_pressure = sorted(
                    {parse(x["pressure_mpa"]) for x in rows})
                branches = {}
                for row in rows:
                    key = (
                        parse(
                            row["power_kw"]), parse(
                            row["pressure_mpa"]), row["cooling"])
                    branches.setdefault(key, []).append(dict(row))
                index[table["table_number"]] = (
                    axis_power, axis_pressure, branches, {parse(x["power_kw"]): x["power_kw"] for x in rows}, {parse(x["pressure_mpa"]): x["pressure_mpa"] for x in rows})
            self._indexes = {identity: index}
        powers, pressures, branches, power_text, pressure_text = self._indexes[identity][number]
        refs.update(
            table_number=number, power_field=power_key, raw_power=str(
                values[power_key]), raw_pressure_mpa=str(
                values["rated_discharge_pressure_mpa"]))
        if not powers[0] <= power <= powers[-1]:
            return result("OUT_OF_STANDARD_SCOPE", "POWER_OUT_OF_SCOPE")
        lower = Fraction("0.4") if number == 4 else Fraction(
            "0.25") if number <= 3 else pressures[0]
        upper = Fraction("1.4") if number <= 4 else pressures[-1]
        if not lower <= pressure <= upper:
            return result("OUT_OF_STANDARD_SCOPE", "PRESSURE_OUT_OF_SCOPE")
        if not pressures[0] <= pressure <= pressures[-1]:
            return result("INSUFFICIENT_DATA", "NO_LOOKUP_BRANCH")
        p = next(x for x in powers if x >= power)
        q = next(x for x in reversed(pressures) if x <= pressure)
        cooling = values.get(
            "cooling_method") if number <= 4 else "NOT_APPLICABLE"
        refs.update(
            selected_power_kw=power_text[p],
            selected_pressure_mpa=pressure_text[q],
            cooling_method=cooling,
            method="POWER_CEILING_PRESSURE_FLOOR")
        selected_rows = branches.get((p, q, cooling), [])
        if not selected_rows:
            return result("INSUFFICIENT_DATA", "COOLING_UNRESOLVED")
        if len(selected_rows) != 3 or {x["grade"]
                                       for x in selected_rows} != {1, 2, 3}:
            raise CompressorPackError("空压机等级分支不完整")
        selected_rows.sort(key=lambda x: x["grade"])
        refs["source_cells"] = [dict(x) for x in selected_rows]
        thresholds = {f"grade_{x['grade']}": dict(state="NO_INDICATOR" if x["value"] is None else "AVAILABLE", value=x["value"],
                                                  display_text=x["source_display"], source_cell=x["source_cell"]) for x in selected_rows}
        if any(x["value"] is None for x in selected_rows):
            return result("INSUFFICIENT_DATA", "SOURCE_DASH",
                          thresholds=thresholds)
        limits = [parse(x["value"]) for x in selected_rows]
        if not limits[0] <= limits[1] <= limits[2]:
            raise CompressorPackError("空压机限值顺序错误")
        grade = next((str(i) for i, limit in enumerate(limits, 1)
                     if nums["specific_power_kw_per_m3_min"] <= limit), None)
        return CompressorEvaluation(
            "SUCCESS", grade, f"{grade}级" if grade else "未达3级", thresholds=thresholds, references=refs)
