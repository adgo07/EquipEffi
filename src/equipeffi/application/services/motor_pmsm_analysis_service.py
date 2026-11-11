"""Application projection of the GB 30253 candidate evaluation and snapshots."""
from copy import deepcopy

from .motor_analysis_service import MotorAnalysisResult, MotorAnalysisService, RESULT_CONTRACT_VERSION, snapshot_value
from ...domain.devices.motor.product_input_contract import MOTOR_PRODUCT_INPUT_CONTRACT, MOTOR_V5_REVISION
from ...domain.devices.motor_pmsm.calculator import Gb30253MotorCalculator, ISSUE_003, RULE_VERSION
from ...domain.devices.motor_pmsm.input_contract import BRANCHES, STANDARD_CODE
from ...domain.devices.motor_pmsm.pack import PACK_ID, PmsmPack

_REASONS = {
    "MISSING_FIELD": "缺少必要参数，请补充所列字段。",
    "INPUT_INVALID": "输入数值无效，请核对字段范围和单位。",
    "CATEGORY_INVALID": "请选择对应的永磁同步电动机类别。",
    "FREQUENCY_OUT_OF_SCOPE": "异步起动类别要求额定频率50 Hz。",
    "VOLTAGE_OUT_OF_SCOPE": "额定电压超出所选类别范围，请核对电压及单位。",
    "COOLING_OUT_OF_SCOPE": "所选类别的标准表未列此冷却方式。",
    "POWER_OUT_OF_SCOPE": "额定功率超出所选类别范围。",
    "POLES_OUT_OF_SCOPE": "极数超出所选类别范围。",
    "SPEED_OUT_OF_SCOPE": "额定转速超出所选类别范围。",
    "NO_POLE_COLUMN": "所选表未列该极数的效率限值。",
    "NO_SPEED_ENDPOINT": "所选表缺少对应的转速区间或合法插值端点。",
    "NO_POWER_ENDPOINT": "所选表缺少合法的功率插值端点。",
    "NO_THRESHOLD": "所选参数在标准表中缺少有效效率限值。",
}
_NUMERIC_UNITS = {
    "rated_voltage_v": "V", "rated_frequency_hz": "Hz", "rated_output_power_kw": "kW",
    "poles": "count", "rated_speed_rpm": "r/min", "rated_efficiency_pct": "percent_point",
}
_BRANCH_INPUTS = frozenset(_NUMERIC_UNITS) | {"cooling_method", "max_nameplate_speed_rpm"}


class MotorPmsmAnalysisService(MotorAnalysisService):
    standard_code = STANDARD_CODE
    standard_version = "2024"
    rule_profile = "motor_pmsm"
    ruleset_version = f"GB30253-A.2/{RULE_VERSION}"
    input_contract = MOTOR_PRODUCT_INPUT_CONTRACT

    def __init__(self, pack: PmsmPack, calculator: Gb30253MotorCalculator, *, records=None, app_version=""):
        self._pack = pack
        self._calculator = calculator
        self._records = records
        self._pack_sha256 = pack.resource_sha256
        self.app_version = app_version

    def _record_ruleset_version(self):
        return self.ruleset_version

    def evaluate(self, request):
        if request.standard_code != STANDARD_CODE:
            raise ValueError("永磁同步电动机请求标准不一致")
        values = deepcopy(request.values)
        if values.get("input_contract_revision") not in (None, "", MOTOR_V5_REVISION):
            raise ValueError("永磁同步电动机使用motor-input.v5契约")
        for key in ("rated_voltage_kv", "measured_efficiency_pct", "efficiency_at_90pct_speed"):
            if values.get(key) not in (None, ""):
                raise ValueError("永磁额定输入不得混用旧kV或实测效率字段")
        category = values.get("category_id")
        branch = BRANCHES.get(category) if isinstance(category, str) else None
        fields = {field.field_id: field for field in branch.fields} if branch else {}
        values = {key: value for key, value in values.items() if key not in _BRANCH_INPUTS or key in fields}
        evaluated = self._calculator.evaluate(values, self._pack)
        refs = snapshot_value(evaluated.references) | {
            "standard_code": STANDARD_CODE, "standard_year": self.standard_version, "canonical_version": "A.2",
            "canonical_package_hash": self._pack_sha256, "pack_id": PACK_ID,
            "result_contract_version": RESULT_CONTRACT_VERSION, "ruleset_version": self.ruleset_version,
            "source_identity": snapshot_value(self._pack.source_files),
        }
        thresholds = {key: dict(value, state="AVAILABLE", display_text=value["display"])
                      for key, value in evaluated.thresholds.items()}
        normalized = {key: value.strip() if isinstance(value, str) else value for key, value in values.items()}
        normalized.update(
            input_contract_revision=MOTOR_V5_REVISION,
            raw_input=values,
            normalized_numeric_values=snapshot_value(evaluated.normalized_numbers),
            input_units={key: unit for key, unit in _NUMERIC_UNITS.items() if key in fields},
        )
        explanation = " ".join(_REASONS[code] for code in evaluated.reason_codes)
        for prefix, keys in (("缺少", evaluated.missing_fields), ("请核对", evaluated.invalid_fields)):
            if keys:
                labels = [fields[key].label if key in fields else "设备类别" for key in keys]
                explanation += f" {prefix}：" + "、".join(labels) + "。"
        if refs.get("above_effective_max_power"):
            explanation += f" 表1的12极有效功率上限为{refs['effective_max_power_kw']} kW。"
        if refs["standard_issues"].get(ISSUE_003) == "PROVISIONAL":
            explanation += " 500至600 r/min衔接采用临时解释。"
        if thresholds and any(lookup.get("method", "").endswith("INTERPOLATION")
                              for lookup in refs.get("grade_lookups", {}).values()):
            explanation += " 插值限值显示两位小数，等级按未修约值比较。"
        trace = {
            "standard_id": refs["standard_id"], "branch": refs.get("branch"), "table_numbers": refs.get("table_numbers", []),
            "grade_lookups": refs.get("grade_lookups", {}), "standard_issues": refs["standard_issues"],
            "poles": normalized.get("poles"), "rated_speed_rpm": normalized.get("rated_speed_rpm"),
        }
        return MotorAnalysisResult(
            product_category=branch.category.label if branch else str(category or ""), as_of=request.as_of,
            evaluation_status=evaluated.evaluation_status, grade=evaluated.grade,
            ui_conclusion=evaluated.ui_conclusion, thresholds=thresholds,
            explanation=explanation.strip(), missing_fields=evaluated.missing_fields,
            invalid_fields=evaluated.invalid_fields, reason_codes=evaluated.reason_codes,
            trace=trace, raw_values=snapshot_value(normalized), references=refs,
            standard_code=STANDARD_CODE, support_status="IMPLEMENTED",
        )

    def standard_overview(self):
        return {"standard_code": STANDARD_CODE, "name": "永磁同步电动机能效限定值及能效等级",
                "edition": self.standard_version, "effective_date": "2025-10-01", "support_status": "IMPLEMENTED",
                "scope_text": "一般用途或防爆用途、连续工作制的永磁同步电动机，含低压/高压异步起动、低压/高压变频调速和电梯用。",
                "notes": "候选已实现，待独立验收。"}
