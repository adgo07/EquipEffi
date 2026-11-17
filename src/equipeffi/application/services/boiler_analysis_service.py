"""锅炉同核Application及不可变历史；不新增持久化结构。"""
from copy import deepcopy
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4
from ..lifecycle import RecordSnapshot, stable_fingerprint
from ...domain.devices.boiler.input_contract import CONTRACT, REVISION, STANDARD_CODE
from ...domain.devices.boiler.calculator import exact_decimal, PROFILE_ID
RESULT_CONTRACT_VERSION = "boiler-result.v1"


def snapshot_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        return {item.name: snapshot_value(
            getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): snapshot_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [snapshot_value(item) for item in value]
    return value


def _threshold_display_projection(thresholds):
    return {key: value.get("display_text")
            for key, value in thresholds.items()}


@dataclass(frozen=True)
class BoilerAnalysisRequest:
    values: dict[str, Any]
    as_of: date = field(default_factory=date.today)
    standard_code: str | None = None


@dataclass(frozen=True)
class BoilerAnalysisResult:
    product_category: str
    as_of: date
    evaluation_status: str | None
    grade: str | None
    ui_conclusion: str
    thresholds: dict[str, Any]
    explanation: str
    missing_fields: tuple[str, ...]
    trace: Any
    raw_values: dict[str, Any]
    references: dict[str, Any]
    standard_code: str = STANDARD_CODE
    support_status: str = "IMPLEMENTED"
    minimum_limit: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()

    @property
    def thresholds_display(self) -> dict[str, str | None]:
        return _threshold_display_projection(self.thresholds)

    @property
    def finalizable(self) -> bool:
        return self.evaluation_status in {
            "SUCCESS", "OUT_OF_STANDARD_SCOPE", "INSUFFICIENT_DATA"}

    def as_snapshot(self) -> dict[str, Any]:
        result = snapshot_value(asdict(self))
        result["as_of"] = self.as_of.isoformat()
        result["finalizable"] = self.finalizable
        return result


@dataclass(frozen=True)
class BoilerAnalysisOutcome:
    result: BoilerAnalysisResult
    record: RecordSnapshot | None
    record_status: str
    record_error: str = ""


REASONS = {"CATEGORY_INVALID": "请选择锅炉类别。", "CONTRACT_INVALID": "锅炉输入请使用V6.7模板。",
           "INPUT_INVALID": "请补充或修正必要参数。", "OTHER_CATEGORY": "所选类别不在本标准范围。",
           "CATEGORY_UNCERTAIN": "设备类别不确定，无法判定。", "NOT_OPEN": "有机热载体锅炉尚未开放。",
           "RANGE_EXCLUDED": "已知额定参数不在本标准范围。", "MIXED_FUEL": "混烧或燃料不能唯一归类，无法判定；请向维护者提供具体燃料和工况资料。",
           "COAL_MISMATCH": "煤种与煤质未匹配当前燃烧方式的表分支，无法判定。",
           "DESIGN_LIMIT_NONPOSITIVE": "设计限定值必须大于0。"}


def get_boiler_input_contract(): return CONTRACT


def boiler_numeric_text_issue(text):
    try:
        exact_decimal(text, numeric_profile_id=PROFILE_ID)
    except ValueError as e:
        return str(e)
    return None


class BoilerAnalysisService:
    def __init__(self, pack, calculator, *, records=None,
                 pack_sha256="", app_version=""):
        self._pack = deepcopy(pack)
        self._calculator = calculator
        self._records = records
        self._pack_sha256 = pack_sha256
        self.app_version = app_version

    standard_code = STANDARD_CODE
    standard_version = "2020"
    rule_profile = "boiler"
    ruleset_version = "GB24500-2020/boiler-grade-rule.v1"
    @property
    def input_contract(self): return CONTRACT

    def evaluate(self, request):
        if request.standard_code not in (None, STANDARD_CODE):
            raise ValueError("锅炉请求标准不一致")
        values = deepcopy(request.values)
        evaluated = self._calculator.evaluate(values, self._pack)
        refs = snapshot_value(evaluated.references) | dict(standard_code=STANDARD_CODE, standard_year="2020", canonical_version="gb24500-2020.owner-20261023.v1",
                                                           canonical_package_hash=self._pack_sha256, pack_id="gb24500_2020_candidate", result_contract_version="boiler-result.v1",
                                                           source_identity=deepcopy(self._pack["source_files"]))
        normalized = snapshot_value(values)
        normalized.update(
            input_contract_revision=REVISION,
            raw_input=snapshot_value(values))
        normalized["normalized_numeric_values"] = {}
        fields = CONTRACT.visible_fields(values.get("category_id"), values)
        for f in fields:
            if f.unit and values.get(f.field_id) not in (None, ""):
                try:
                    x = exact_decimal(
                        values[f.field_id], numeric_profile_id=PROFILE_ID)
                    normalized["normalized_numeric_values"][f.field_id] = {"numerator": str(
                        x.numerator), "denominator": str(x.denominator), "unit": f.unit}
                except ValueError:
                    pass
        explanation = "；".join(REASONS[code] for code in evaluated.reason_codes)
        if evaluated.minimum_limit:
            limit = evaluated.minimum_limit
            label = "设计限定值" if limit["source_kind"] == "OWNER_DESIGN_LIMIT" else "限定值"
            explanation = f"{label} {limit['value']}%；" + ("达到" if limit["met"] else "未达到") + label + "。所填热效率对应以上结论。"
        labels = {
            f.field_id: f.label for f in fields} | {
            "category_id": "设备类别"}
        if evaluated.missing_fields:
            explanation += " 缺少：" + \
                "、".join(labels.get(k, k) for k in evaluated.missing_fields)
        if evaluated.invalid_fields:
            explanation += " 请核对：" + \
                "、".join(labels.get(k, "输入字段")
                         for k in evaluated.invalid_fields)
        category = next(
            (c.label for c in CONTRACT.categories if c.category_id ==
             values.get("category_id")),
            "")
        return BoilerAnalysisResult(category, request.as_of, evaluated.evaluation_status, evaluated.grade, evaluated.ui_conclusion,
                                        snapshot_value(
                                            evaluated.thresholds), explanation, evaluated.missing_fields, refs, normalized, refs,
                                        standard_code=STANDARD_CODE, support_status="IMPLEMENTED" if evaluated.evaluation_status is not None else "MAPPING", minimum_limit=snapshot_value(evaluated.minimum_limit), reason_codes=evaluated.reason_codes, invalid_fields=evaluated.invalid_fields)

    def standard_overview(self):
        return dict(standard_code=STANDARD_CODE, name="工业锅炉能效限定值及能效等级", edition="2020", effective_date="2021-06-01",
                    support_status="IMPLEMENTED", scope_text="固定式水介质蒸汽／热水锅炉；有机热载体未开放。", notes="已实现，待验收")

    def _record_ruleset_version(self) -> str:
        return str(self._pack.get("mapping_revision", self.ruleset_version))

    def analyze_and_record(
            self, request: BoilerAnalysisRequest) -> BoilerAnalysisOutcome:
        result = self.evaluate(request)
        if not result.finalizable:
            return BoilerAnalysisOutcome(result, None, "NOT_ELIGIBLE")
        if self._records is None:
            return BoilerAnalysisOutcome(
                result, None, "SAVE_FAILED", "未装配历史记录存储")
        now = datetime.now(timezone.utc).isoformat()
        references = result.references
        inputs = deepcopy(result.raw_values)
        inputs["request_fingerprint"] = stable_fingerprint(
            inputs | {"standard_code": self.standard_code, "as_of": request.as_of.isoformat()})
        record = RecordSnapshot(
            record_id=f"BO-{uuid4().hex}", workspace_id=None,
            standard_code=self.standard_code, standard_version=self.standard_version,
            device_type=self.rule_profile, product_category=result.product_category,
            rule_profile=self.rule_profile, as_of=request.as_of.isoformat(),
            evaluation_status=str(result.evaluation_status), grade=result.grade,
            ui_conclusion=result.ui_conclusion, input_snapshot=inputs,
            result_snapshot=result.as_snapshot(), reference_snapshot=deepcopy(references),
            ruleset_version=self._record_ruleset_version(),
            calculator_version=str(references["calculator_version"]),
            numeric_profile_id=str(references["numeric_profile_id"]),
            canonical_version=str(references["canonical_version"]),
            canonical_package_hash=self._pack_sha256,
            result_contract_version=RESULT_CONTRACT_VERSION,
            schema_version=1, created_at_utc=now, finalized_at_utc=now)
        try:
            self._records.append_record(record)
        except Exception as error:
            return BoilerAnalysisOutcome(
                result, None, "SAVE_FAILED", f"{type(error).__name__}: {error}")
        return BoilerAnalysisOutcome(result, record, "SAVED")


def boiler_requires_design_limit(category, qnet):
    from ...domain.devices.boiler.input_contract import is_low_biomass
    return is_low_biomass(category, qnet)
