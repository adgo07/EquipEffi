"""GB 30254—2024 六表候选内核：精确十进制输入与有理数插值。"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import re
from typing import Any, Mapping

PROFILE_ID = "EQUIPEFFI_MOTOR_HV_EXACT_LINEAR_V1"
CALCULATOR_VERSION = "gb30254-motor-hv-v1.0.0-candidate"
_LEXEME = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_NUMERIC = ("rated_voltage_v", "rated_frequency_hz", "rated_output_power_kw", "poles", "rated_efficiency_pct")
_COOLING = (("IC01", "IC11", "IC21", "IC31", "IC81W"), ("IC611", "IC616", "IC511", "IC516"), ("IC411",))


class HvPackError(RuntimeError):
    """标准资产或数值配置错误；不转换为合法业务终态。"""


@dataclass(frozen=True)
class HvEvaluation:
    evaluation_status: str
    grade: str | None
    ui_conclusion: str
    reason_codes: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()
    thresholds: Mapping[str, Any] = field(default_factory=dict)
    references: Mapping[str, Any] = field(default_factory=dict)


class _ExactProfile:
    """所有数值操作只在已核验的独立Profile实例上执行。"""

    def __init__(self, profile_id: str):
        if profile_id != PROFILE_ID:
            raise HvPackError("高压电机Numeric Profile不匹配")
        self.profile_id = profile_id

    def parse(self, value: Any) -> Fraction:
        if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
            raise ValueError("必须为精确十进制词法、整数或Decimal，拒绝float")
        if isinstance(value, int) and value.bit_length() > 100:
            raise ValueError("整数超过输入上限")
        text = str(value).strip()
        if len(text) > 128 or not _LEXEME.fullmatch(text):
            raise ValueError("无效十进制词法")
        mantissa, _, exponent = text.lower().partition("e")
        if len(re.sub(r"[^0-9]", "", mantissa)) > 30 or abs(int(exponent or "0")) > 30:
            raise ValueError("数值超过输入上限")
        return Fraction(text)

    def interpolate(self, low: Fraction, high: Fraction, weight: Fraction) -> Fraction:
        return low + (high - low) * weight

    def reaches(self, value: Fraction, threshold: Fraction) -> bool:
        return value >= threshold

    def snapshot(self, value: Fraction) -> dict[str, str]:
        return {"numerator": str(value.numerator), "denominator": str(value.denominator), "unit": "percent_point"}

    def display(self, value: Fraction) -> str:
        # 正效率的ROUND_HALF_UP，两位小数；绝不反送到比较路径。
        whole, remainder = divmod(value.numerator * 100, value.denominator)
        whole += int(remainder * 2 >= value.denominator)
        return f"{whole // 100}.{whole % 100:02d}"


class Gb30254MotorCalculator:
    calculator_version = CALCULATOR_VERSION
    numeric_profile_id = PROFILE_ID

    def evaluate(self, values: Mapping[str, Any], pack: Mapping[str, Any], *,
                 numeric_profile_id: str = PROFILE_ID) -> HvEvaluation:
        numeric = _ExactProfile(numeric_profile_id)
        self._validate_pack(pack)
        refs = {"standard_id": "GB30254-2024", "numeric_contract_version": "v1",
                "numeric_profile_id": numeric.profile_id, "calculator_version": CALCULATOR_VERSION,
                "pack_sha256": pack["integrity_sha256"], "standard_issues": ["EQP-STD-GB30254-001", "EQP-STD-GB30254-002", "EQP-STD-MOTOR-009"]}

        def result(status: str, reason: str, **kwargs: Any) -> HvEvaluation:
            label = {"INVALID_INPUT": "输入错误", "INSUFFICIENT_DATA": "无法判定",
                     "OUT_OF_STANDARD_SCOPE": "不在范围"}[status]
            return HvEvaluation(status, None, label, (reason,), references=refs, **kwargs)

        parsed: dict[str, Fraction | str] = {}
        missing, invalid = [], []
        for name in ("category_id", "cooling_method", *_NUMERIC):
            raw = values.get(name)
            if raw is None or isinstance(raw, str) and not raw.strip():
                missing.append(name)
                continue
            if name not in _NUMERIC:
                if not isinstance(raw, str) or len(raw) > 128:
                    invalid.append(name)
                else:
                    parsed[name] = raw.strip()
                continue
            try:
                value = numeric.parse(raw)
                if value <= 0 or name == "rated_efficiency_pct" and not 1 <= value <= 100:
                    raise ValueError("数值范围无效")
                if name == "poles" and (value.denominator != 1 or value.numerator % 2):
                    raise ValueError("极数必须为正偶数")
                parsed[name] = value
            except ValueError:
                # 明确频率范围是有效证据，但不属于50Hz；非有限/非法词法仍拒绝。
                if name == "rated_frequency_hz" and isinstance(raw, str) and len(raw) <= 128 and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?\s*[-~～]\s*[0-9]+(?:\.[0-9]+)?", raw.strip()):
                    parsed[name] = raw.strip()
                else:
                    invalid.append(name)
        if invalid:
            return result("INVALID_INPUT", "INPUT_INVALID", invalid_fields=tuple(invalid))
        category = parsed.get("category_id")
        if category == "OTHER_CATEGORY":
            return result("OUT_OF_STANDARD_SCOPE", "OTHER_CATEGORY")
        if category == "UNCERTAIN_CATEGORY":
            return result("INSUFFICIENT_DATA", "CATEGORY_UNCERTAIN")
        if category is not None and category != "gb30254_cage_induction":
            return result("INVALID_INPUT", "CATEGORY_INVALID", invalid_fields=("category_id",))
        if missing:
            return result("INSUFFICIENT_DATA", "MISSING_FIELD", missing_fields=tuple(missing))
        if parsed["rated_frequency_hz"] != 50:
            return result("OUT_OF_STANDARD_SCOPE", "FREQUENCY_OUT_OF_SCOPE")
        voltage = parsed["rated_voltage_v"]
        if voltage not in (3000, 3300, 6000, 10000):
            return result("OUT_OF_STANDARD_SCOPE", "VOLTAGE_OUT_OF_SCOPE")
        group = next((i for i, codes in enumerate(_COOLING) if parsed["cooling_method"] in codes), None)
        if group is None:
            return result("OUT_OF_STANDARD_SCOPE", "COOLING_OUT_OF_SCOPE")
        table_number = 2 * group + (2 if voltage == 10000 else 1)
        table = pack["tables"][table_number - 1]
        pole = int(parsed["poles"])
        refs.update(table_number=table_number, poles=pole)
        if pole not in table["poles"]:
            return result("OUT_OF_STANDARD_SCOPE", "NO_POLE_COLUMN")
        power = parsed["rated_output_power_kw"]
        rows = table["rows"]
        upper = next((i for i, row in enumerate(rows) if numeric.parse(row["power_kw"]) >= power), None)
        if upper is None:
            return result("OUT_OF_STANDARD_SCOPE", "NO_THRESHOLD")
        if numeric.parse(rows[upper]["power_kw"]) == power:
            endpoints, weight = [rows[upper]], Fraction(0)
        elif upper == 0:
            return result("OUT_OF_STANDARD_SCOPE", "NO_THRESHOLD")
        else:
            endpoints = [rows[upper - 1], rows[upper]]
            lo, hi = (numeric.parse(row["power_kw"]) for row in endpoints)
            weight = (power - lo) / (hi - lo)
        source = [row["branches"][str(pole)] for row in endpoints]
        refs.update(method="DIRECT" if len(endpoints) == 1 else "LINEAR_INTERPOLATION",
                    endpoint_power_kw=[row["power_kw"] for row in endpoints],
                    source_cells=[[item["source_cell"] for item in branch] for branch in source],
                    test_method_reference="GB/T 1032—2023 §12.3 B法" if power <= 2000 else "GB/T 1032—2023 §12.8 H法（杂散损耗推荐值）")
        if any(item["value"] is None for branch in source for item in branch):
            return result("OUT_OF_STANDARD_SCOPE", "NO_THRESHOLD")
        thresholds, exact = {}, []
        for i in range(3):
            low = numeric.parse(source[0][i]["value"])
            high = numeric.parse(source[-1][i]["value"])
            value = numeric.interpolate(low, high, weight)
            exact.append(value)
            thresholds[f"grade_{i + 1}"] = {"exact": numeric.snapshot(value),
                "display": source[0][i]["source_display"] if len(source) == 1 else numeric.display(value)}
        grade = next((str(i) for i, threshold in enumerate(exact, 1)
                      if numeric.reaches(parsed["rated_efficiency_pct"], threshold)), None)
        return HvEvaluation("SUCCESS", grade, f"{grade}级" if grade else "未达3级",
                            thresholds=thresholds, references=refs)

    @staticmethod
    def _validate_pack(pack: Mapping[str, Any]) -> None:
        try:
            payload = {key: value for key, value in pack.items() if key != "integrity_sha256"}
            digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")).encode()).hexdigest()
            if (pack["schema_version"] != "equipeffi.motor-hv-candidate.v1"
                    or pack["standard_id"] != "GB30254-2024"
                    or pack["numeric_profile_id"] != PROFILE_ID
                    or digest != pack["integrity_sha256"]):
                raise HvPackError("高压电机候选包身份或完整性错误")
            # 独立候选版本只接受本次批准源生成的确切包，禁止篡改后重签。
            from .pack_identity import PACK_SHA256
            if digest != PACK_SHA256:
                raise HvPackError("高压电机候选包与版本固定资产不一致")
        except (KeyError, TypeError, ValueError) as exc:
            raise HvPackError("高压电机候选包损坏") from exc
