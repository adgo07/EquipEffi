"""Explicit standard routing for the shared Qt/Excel motor product flow."""
from dataclasses import replace
from copy import deepcopy
from .motor_analysis_service import MotorAnalysisService, MotorAnalysisResult, snapshot_value
from ...domain.devices.motor_hv.input_contract import HV_CATEGORY_ID, HV_CATEGORY, MOTOR_PRODUCT_INPUT_CONTRACT
from ...domain.devices.motor_hv.input_contract import HV_FIELDS

HV_STANDARD = "GB 30254-2024"
_REASONS = {
    "MISSING_FIELD": "缺少必要参数，请补充所列字段。", "INPUT_INVALID": "输入数值无效，请核对字段范围和单位。",
    "CATEGORY_INVALID": "请选择已登记的高压电动机类别。", "OTHER_CATEGORY": "所选类别不在本标准范围。",
    "CATEGORY_UNCERTAIN": "设备类别不确定，无法判定。", "FREQUENCY_OUT_OF_SCOPE": "额定频率不是50 Hz，不在本标准范围。",
    "VOLTAGE_OUT_OF_SCOPE": "额定电压不在3000、3300、6000、10000 V表定范围。",
    "COOLING_OUT_OF_SCOPE": "冷却代码无对应表。", "NO_POLE_COLUMN": "所选表没有该极数列。",
    "NO_THRESHOLD": "所选表、极数及功率无有效阈值；不补值或外推。",
}


class MotorHvAnalysisService(MotorAnalysisService):
    standard_code = HV_STANDARD
    standard_version = "2024"
    rule_profile = "motor_hv"
    ruleset_version = "GB30254-A.3/motor-hv-rule.v1"

    @property
    def input_contract(self):
        return MOTOR_PRODUCT_INPUT_CONTRACT

    def evaluate(self, request):
        if request.standard_code != HV_STANDARD:
            raise ValueError("高压电动机请求标准不一致")
        values = deepcopy(request.values)
        if values.get("input_contract_revision") not in (None, "", "motor-input.v4"):
            raise ValueError("高压电动机仅接受motor-input.v4契约")
        for key in ("rated_voltage_kv", "measured_efficiency_pct"):
            if values.get(key) not in (None, ""):
                raise ValueError("高压额定输入不得混用旧kV或实测效率字段")
        evaluated = self._calculator.evaluate(values, self._pack)
        refs = snapshot_value(evaluated.references) | {
            "standard_code": HV_STANDARD, "standard_year": "2024", "canonical_version": "A.3",
            "canonical_package_hash": self._pack_sha256, "pack_id": "gb30254_2024_candidate",
            "result_contract_version": "motor-result.v1", "rule_version": "motor-hv-rule.v1",
            "source_identity": deepcopy(self._pack.get("source_files", {})),
        }
        thresholds = {key: dict(value, state="AVAILABLE", display_text=value["display"])
                      for key, value in evaluated.thresholds.items()}
        trace = dict(refs, table_no=refs.get("table_number"),
                     rated_output_power_kw=snapshot_value(values.get("rated_output_power_kw")),
                     power_endpoints=refs.get("endpoint_power_kw", []))
        trace["sources"] = [{"source_sheet": cell.split("!")[0], "source_cell": cell.split("!")[-1]}
            for row in refs.get("source_cells", ()) for cell in row]
        normalized = {key: value.strip() if isinstance(value, str) else value
                      for key, value in values.items()}
        # Record the effective exact parsed numeric values separately from raw
        # lexical evidence. This uses the same declared ingress as Calculator.
        from ...domain.devices.motor_hv.calculator import _ExactProfile, PROFILE_ID
        ingress = _ExactProfile(PROFILE_ID)
        exact_inputs = {}
        for key in ("rated_voltage_v", "rated_frequency_hz", "rated_output_power_kw", "poles", "rated_efficiency_pct"):
            if normalized.get(key) not in (None, ""):
                try:
                    number = ingress.parse(normalized[key])
                    exact_inputs[key] = {"numerator": str(number.numerator), "denominator": str(number.denominator)}
                except ValueError:
                    pass  # Text frequency and rejected input retain their raw evidence.
        normalized["normalized_numeric_values"] = exact_inputs
        normalized["input_contract_revision"] = "motor-input.v4"
        normalized["input_units"] = {"rated_voltage_v": "V", "rated_frequency_hz": "Hz",
            "rated_output_power_kw": "kW", "poles": "count", "rated_efficiency_pct": "percent_point"}
        normalized["raw_input"] = deepcopy(values)
        labels = {field.field_id: field.label for field in HV_FIELDS} | {"category_id": "设备类别"}
        explanation = "；".join(_REASONS.get(code, code) for code in evaluated.reason_codes)
        if evaluated.missing_fields:
            explanation += " 缺少：" + "、".join(labels.get(key, key) for key in evaluated.missing_fields)
        if evaluated.invalid_fields:
            explanation += " 请核对：" + "、".join(labels.get(key, key) for key in evaluated.invalid_fields)
        if (evaluated.evaluation_status == "SUCCESS" and thresholds
                and refs.get("method") == "LINEAR_INTERPOLATION"):
            explanation += "插值限值显示为两位小数，等级按未修约值比较。"
        return MotorAnalysisResult(
            product_category=next((item.label for item in self.input_contract.categories
                if item.category_id == normalized.get("category_id")), str(normalized.get("category_id") or "")), as_of=request.as_of,
            evaluation_status=evaluated.evaluation_status, grade=evaluated.grade,
            ui_conclusion=evaluated.ui_conclusion, thresholds=thresholds,
            explanation=explanation,
            missing_fields=evaluated.missing_fields, invalid_fields=evaluated.invalid_fields,
            reason_codes=evaluated.reason_codes, trace=trace,
            raw_values=snapshot_value(normalized), references=refs,
            standard_code=HV_STANDARD, support_status="IMPLEMENTED")

    def standard_overview(self):
        return {"standard_code": HV_STANDARD, "name": "高压三相笼型异步电动机能效限定值及能效等级",
            "edition": "2024", "effective_date": "2025-09-01", "support_status": "IMPLEMENTED",
            "scope_text": "高压三相笼型异步电动机；表1至表6，50 Hz，3000/3300/6000/10000 V。",
            "notes": "候选已实现，待独立验收；尚未正式支持。"}


class MotorProductService:
    def __init__(self, low_voltage, high_voltage):
        self.low_voltage, self.high_voltage = low_voltage, high_voltage
        self.input_contract = MOTOR_PRODUCT_INPUT_CONTRACT
        self.app_version = low_voltage.app_version
        self._records = low_voltage._records

    def _route(self, request):
        high = request.values.get("category_id") == HV_CATEGORY_ID
        if request.standard_code == HV_STANDARD:
            return self.high_voltage, request
        if high:
            if request.standard_code is not None:
                raise ValueError("明确选择的标准与高压类别不一致")
            return self.high_voltage, replace(request, standard_code=HV_STANDARD)
        return self.low_voltage, request

    def evaluate(self, request):
        service, routed = self._route(request)
        return service.evaluate(routed)

    def analyze_and_record(self, request):
        service, routed = self._route(request)
        return service.analyze_and_record(routed)

    def standard_overview(self):
        return self.low_voltage.standard_overview()

    def standard_overviews(self):
        return [self.low_voltage.standard_overview(), self.high_voltage.standard_overview()]
