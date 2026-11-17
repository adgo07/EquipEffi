"""GB24500精确阈值比较，独立于UI/Excel/持久化。"""
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json
import re
from .input_contract import BY_ID, CONTRACT, REVISION

PROFILE_ID = "EQUIPEFFI_BOILER_EXACT_LOOKUP_V1"
CALCULATOR_VERSION = "gb24500-boiler-v1.0.0-candidate"
LEXEME = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class BoilerPackError(RuntimeError):
    """资源或Profile错误，不能变成业务无法判定。"""


def exact_decimal(value, *, numeric_profile_id):
    if numeric_profile_id != PROFILE_ID:
        raise BoilerPackError("锅炉Numeric Profile不匹配")
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("须为精确十进制，拒绝float")
    text = str(value).strip()
    if len(text) > 128 or not LEXEME.fullmatch(text):
        raise ValueError("十进制格式无效")
    mantissa, _, exponent = text.lower().partition("e")
    if len(re.sub(r"[^0-9]", "", mantissa)) > 30 or abs(int(exponent or "0")) > 30:
        raise ValueError("数值超过输入上限")
    return Fraction(text)


def _condition_matches(source, variable, value, parse):
    expression = source.replace(variable, "x")
    tokens = re.findall(r"x|[0-9]+(?:\.[0-9]+)?|≤|≥|<|>", expression)
    if "".join(tokens) != expression or len(tokens) not in {3, 5}:
        raise BoilerPackError("煤质源条件不能解析")
    for i in range(0, len(tokens) - 2, 2):
        a, op, b = tokens[i:i + 3]
        left, right = (value if a == "x" else parse(a)), (value if b == "x" else parse(b))
        if not {"≤": left <= right, "≥": left >= right, "<": left < right, ">": left > right}[op]:
            return False
    return True


@dataclass(frozen=True)
class BoilerEvaluation:
    evaluation_status: str | None
    grade: str | None
    ui_conclusion: str
    reason_codes: tuple = ()
    missing_fields: tuple = ()
    invalid_fields: tuple = ()
    thresholds: dict = field(default_factory=dict)
    references: dict = field(default_factory=dict)
    minimum_limit: dict = field(default_factory=dict)


class Gb24500BoilerCalculator:
    calculator_version = CALCULATOR_VERSION
    numeric_profile_id = PROFILE_ID

    @staticmethod
    def validate_pack(pack):
        try:
            body = {k: v for k, v in pack.items() if k != "integrity_sha256"}
            digest = sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if digest != pack["integrity_sha256"] or pack["numeric_profile_id"] != PROFILE_ID or pack["standard_id"] != "GB24500-2020":
                raise ValueError("身份不符")
            if len(pack["cells"]) != 78 or pack["electric_limit"]["value"] != "97":
                raise ValueError("源格清单不完整")
        except (KeyError, TypeError, ValueError) as error:
            raise BoilerPackError("锅炉标准包无效") from error

    def evaluate(self, values, pack, *, numeric_profile_id=PROFILE_ID):
        parse = lambda x: exact_decimal(x, numeric_profile_id=numeric_profile_id)
        parse("1")
        self.validate_pack(pack)
        refs = dict(standard_id="GB24500-2020", numeric_contract_version="v1", numeric_profile_id=numeric_profile_id,
                    numeric_profile_version="1.0.0", calculator_version=CALCULATOR_VERSION,
                    rule_version="boiler-grade-rule.v1", pack_sha256=pack["integrity_sha256"],
                    standard_issues=["EQP-STD-GB24500-001", "EQP-STD-GB24500-002"],
                    assessment_scope="DECLARED_EFFICIENCY_ONLY_NO_EMISSIONS")

        def result(status, reason, **kw):
            return BoilerEvaluation(status, None, {"INVALID_INPUT": "输入错误", "OUT_OF_STANDARD_SCOPE": "不在范围",
                "INSUFFICIENT_DATA": "无法判定", None: "未开放"}[status], reason_codes=(reason,), references=dict(refs), **kw)

        category = BY_ID.get(values.get("category_id"))
        if category is None:
            return result("INVALID_INPUT", "CATEGORY_INVALID", invalid_fields=("category_id",))
        if values.get("input_contract_revision") not in (None, "", REVISION):
            return result("INVALID_INPUT", "CONTRACT_INVALID", invalid_fields=("input_contract_revision",))
        if category.category_id == "OTHER_CATEGORY":
            return result("OUT_OF_STANDARD_SCOPE", "OTHER_CATEGORY")
        if category.category_id == "ORGANIC_HEAT_CARRIER":
            return result(None, "NOT_OPEN")
        if category.category_id == "UNCERTAIN_CATEGORY":
            return result("INSUFFICIENT_DATA", "CATEGORY_UNCERTAIN")
        # 已有范围排除优先；非法词法始终是输入问题。
        nums, invalid = {}, []
        numeric_keys = ("rated_capacity", "rated_pressure_mpa", "qnet_kj_kg", "vdaf_pct", "efficiency_pct", "design_limit_pct")
        for key in numeric_keys:
            if values.get(key) in (None, ""):
                continue
            try:
                nums[key] = parse(values[key])
                if nums[key] < 0:
                    invalid.append(key)
            except ValueError:
                invalid.append(key)
        if invalid:
            return result("INVALID_INPUT", "INPUT_INVALID", invalid_fields=tuple(invalid))
        pressure, capacity = nums.get("rated_pressure_mpa"), nums.get("rated_capacity")
        if (pressure is not None and (pressure < Fraction("0.1") or category.form == "steam" and pressure >= Fraction("3.8"))) or (
                category.form == "hot_water" and capacity is not None and capacity < Fraction("0.1")):
            return result("OUT_OF_STANDARD_SCOPE", "RANGE_EXCLUDED")
        if category.heat == "mixed":
            return result("INSUFFICIENT_DATA", "MIXED_FUEL")
        fields = CONTRACT.visible_fields(category.category_id, values)
        missing = tuple(f.field_id for f in fields if f.required and values.get(f.field_id) in (None, ""))
        if missing:
            return result("INVALID_INPUT", "INPUT_INVALID", missing_fields=missing)
        allowed = {f.field_id for f in fields}
        invalid = [key for key in (*numeric_keys, "fuel") if key not in allowed and values.get(key) not in (None, "")]
        # 蒸汽表2/4容量可记录，但不以它增设标准容量范围。
        if "fuel" in allowed and values.get("fuel") not in dict(CONTRACT.options(category.category_id, "fuel")):
            invalid.append("fuel")
        if nums.get("vdaf_pct", 0) > 100:
            invalid.append("vdaf_pct")
        if category.heat == "biomass" and nums["qnet_kj_kg"] <= 0:
            invalid.append("qnet_kj_kg")
        if category.heat in {"layer_coal", "biomass"} and capacity <= 0:
            invalid.append("rated_capacity")
        # Owner 2026-11-17明确：设计限定值必须大于0。
        if "design_limit_pct" in nums and nums["design_limit_pct"] <= 0:
            return result("INVALID_INPUT", "DESIGN_LIMIT_NONPOSITIVE", invalid_fields=("design_limit_pct",))
        if invalid:
            return result("INVALID_INPUT", "INPUT_INVALID", invalid_fields=tuple(invalid))
        refs.update(efficiency_basis=category.basis, product_form=category.form, heat_source=category.heat)
        efficiency = nums["efficiency_pct"]
        if category.heat == "electric":
            limit = dict(pack["electric_limit"], source_kind="CLAUSE_5_2", met=efficiency >= parse(pack["electric_limit"]["value"]))
            return BoilerEvaluation("SUCCESS", None, "达到限定值" if limit["met"] else "未达到限定值", references=refs, minimum_limit=limit)
        table = 1 if category.heat == "layer_coal" else 2 if category.heat == "fluid_coal" else 3 if category.heat == "biomass" else 4
        rows = [r for r in pack["cells"] if r["table_number"] == table]
        if table in {1, 3}:
            boundary = (20 if category.form == "steam" else 14) if table == 1 else (10 if category.form == "steam" else 7)
            bucket = "SMALL" if capacity <= boundary else "LARGE"
            refs["capacity_bucket"] = bucket
            rows = [r for r in rows if r["capacity_bucket"] == bucket]
        if table in {1, 2}:
            rows = [r for r in rows if r["fuel"] == values["fuel"] and
                    _condition_matches(r["qnet_condition"], "Qnet,v,ar", nums["qnet_kj_kg"], parse) and
                    _condition_matches(r["vdaf_condition"], "Vdaf", nums["vdaf_pct"], parse)]
        elif table == 4:
            branch = {"gas": 1, "gas_condensing_lower": 2, "gas_condensing_higher": 3, "oil": 4, "chamber_coal": 5}[category.heat]
            rows = [r for r in rows if r["branch"] == f"T4-B{branch}"]
        refs["table_number"] = table
        if not rows:
            return result("INSUFFICIENT_DATA", "COAL_MISMATCH")
        rows = sorted(rows, key=lambda r: r["grade"])
        if len(rows) != 3 or [r["grade"] for r in rows] != [1, 2, 3]:
            raise BoilerPackError("锅炉分支等级不完整")
        refs["source_cells"] = rows
        thresholds = {f"grade_{r['grade']}": dict(value=r["value"], display_text=r["value"], source_cell=r["source_cell"], source_kind="TABLE_GRADE") for r in rows}
        special = table == 3 and nums["qnet_kj_kg"] < 8374
        if special:
            thresholds["grade_3"] = dict(value=str(values["design_limit_pct"]).strip(), display_text=str(values["design_limit_pct"]).strip(),
                source_kind="OWNER_DESIGN_LIMIT", source_reference="input.design_limit_pct / EQP-STD-GB24500-001",
                original_table_value=rows[2]["value"], original_source_cell=rows[2]["source_cell"])
        third = thresholds["grade_3"]
        minimum = dict(third, source_kind="OWNER_DESIGN_LIMIT" if special else "TABLE_GRADE_3", met=efficiency >= parse(third["value"]))
        grade = next((str(n) for n in (1, 2, 3) if efficiency >= parse(thresholds[f"grade_{n}"]["value"])), None)
        return BoilerEvaluation("SUCCESS", grade, f"{grade}级" if grade else "未达3级", thresholds=thresholds, references=refs, minimum_limit=minimum)
