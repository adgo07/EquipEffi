"""空压机同核Application及不可变历史；不新增持久化结构。"""
from copy import deepcopy
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4
from ..lifecycle import RecordSnapshot, stable_fingerprint
from ...domain.devices.compressor.input_contract import CONTRACT, REVISION, STANDARD_CODE
from ...domain.devices.compressor.calculator import exact_decimal, PROFILE_ID
RESULT_CONTRACT_VERSION = "compressor-result.v1"


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
class CompressorAnalysisRequest:
    values: dict[str, Any]
    as_of: date = field(default_factory=date.today)
    standard_code: str | None = None


@dataclass(frozen=True)
class CompressorAnalysisResult:
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
class CompressorAnalysisOutcome:
    result: CompressorAnalysisResult
    record: RecordSnapshot | None
    record_status: str
    record_error: str = ""


REASONS = {"CATEGORY_INVALID": "请选择空压机类别。", "CONTRACT_INVALID": "输入模板版本不支持，请使用V6.6模板。",
           "INPUT_INVALID": "请补充或修正必要参数。", "OTHER_CATEGORY": "所选类别不在本标准范围。",
           "CATEGORY_UNCERTAIN": "设备类别不确定，无法判定。", "POWER_OUT_OF_SCOPE": "额定功率超出所选表范围。",
           "PRESSURE_OUT_OF_SCOPE": "额定排气压力超出适用范围。", "NO_LOOKUP_BRANCH": "该压力没有可用的标准查表指标。",
           "COOLING_UNRESOLVED": "标准未规定该冷却分支指标。", "SOURCE_DASH": "所选条件的标准表值为横杠，无法判定。"}


def get_compressor_input_contract(): return CONTRACT


def compressor_numeric_text_issue(text):
    try:
        exact_decimal(text, numeric_profile_id=PROFILE_ID)
    except ValueError as e:
        return str(e)
    return None


class CompressorAnalysisService:
    def __init__(self, pack, calculator, *, records=None,
                 pack_sha256="", app_version=""):
        self._pack = deepcopy(pack)
        self._calculator = calculator
        self._records = records
        self._pack_sha256 = pack_sha256
        self.app_version = app_version

    standard_code = STANDARD_CODE
    standard_version = "2019"
    rule_profile = "compressor"
    ruleset_version = "GB19153-A.1/compressor-grade-rule.v1"
    @property
    def input_contract(self): return CONTRACT

    def evaluate(self, request):
        if request.standard_code not in (None, STANDARD_CODE):
            raise ValueError("空压机请求标准不一致")
        values = deepcopy(request.values)
        evaluated = self._calculator.evaluate(values, self._pack)
        refs = snapshot_value(evaluated.references) | dict(standard_code=STANDARD_CODE, standard_year="2019", canonical_version="A.1",
                                                           canonical_package_hash=self._pack_sha256, pack_id="gb19153_2019_candidate", result_contract_version="compressor-result.v1",
                                                           source_identity=deepcopy(self._pack["source_files"]))
        normalized = snapshot_value(values)
        normalized.update(
            input_contract_revision=REVISION,
            raw_input=snapshot_value(values))
        normalized["normalized_numeric_values"] = {}
        fields = CONTRACT.visible_fields(values.get("category_id"))
        for f in fields:
            if f.unit and values.get(f.field_id) not in (None, ""):
                try:
                    x = exact_decimal(
                        values[f.field_id], numeric_profile_id=PROFILE_ID)
                    normalized["normalized_numeric_values"][f.field_id] = {"numerator": str(
                        x.numerator), "denominator": str(x.denominator), "unit": f.unit}
                except ValueError:
                    pass
        explanation = "；".join(REASONS[code]
                               for code in evaluated.reason_codes)
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
        return CompressorAnalysisResult(category, request.as_of, evaluated.evaluation_status, evaluated.grade, evaluated.ui_conclusion,
                                        snapshot_value(
                                            evaluated.thresholds), explanation, evaluated.missing_fields, refs, normalized, refs,
                                        standard_code=STANDARD_CODE, support_status="IMPLEMENTED", reason_codes=evaluated.reason_codes, invalid_fields=evaluated.invalid_fields)

    def standard_overview(self):
        return dict(standard_code=STANDARD_CODE, name="容积式空气压缩机能效限定值及能效等级", edition="2019", effective_date="2020-07-01",
                    support_status="IMPLEMENTED", scope_text="六类容积式空气压缩机，表1至表6。", notes="已实现，待验收")

    def _record_ruleset_version(self) -> str:
        return str(self._pack.get("mapping_revision", self.ruleset_version))

    def analyze_and_record(
            self, request: CompressorAnalysisRequest) -> CompressorAnalysisOutcome:
        result = self.evaluate(request)
        if not result.finalizable:
            return CompressorAnalysisOutcome(result, None, "NOT_ELIGIBLE")
        if self._records is None:
            return CompressorAnalysisOutcome(
                result, None, "SAVE_FAILED", "未装配历史记录存储")
        now = datetime.now(timezone.utc).isoformat()
        references = result.references
        inputs = deepcopy(result.raw_values)
        inputs["request_fingerprint"] = stable_fingerprint(
            inputs | {"standard_code": self.standard_code, "as_of": request.as_of.isoformat()})
        record = RecordSnapshot(
            record_id=f"CO-{uuid4().hex}", workspace_id=None,
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
            return CompressorAnalysisOutcome(
                result, None, "SAVE_FAILED", f"{type(error).__name__}: {error}")
        return CompressorAnalysisOutcome(result, record, "SAVED")
