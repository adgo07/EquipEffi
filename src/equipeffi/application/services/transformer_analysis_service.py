"""GB20052 应用入口；Qt与表格共用，持久化只经既有Record端口。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from ...domain.devices.transformer.input_contract import TRANSFORMER_SCOPE_HINT
from ..lifecycle import RecordSnapshot, stable_fingerprint
from .transformer_basis_formatter import format_transformer_basis_lines


STANDARD_CODE = "GB 20052-2024"
NUMERIC_PROFILE = "EQUIPEFFI_TRANSFORMER_GB20052_DECIMAL50_V1"


def get_transformer_input_contract():
    """只读字段名称与单位，供无当前计算服务的历史页面使用。"""
    from ...domain.devices.transformer.input_contract import TRANSFORMER_INPUT_CONTRACT
    return TRANSFORMER_INPUT_CONTRACT


def snapshot_value(value: Any) -> Any:
    """精确快照，不通过float，不依赖UI展示格式。"""
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        return {item.name: snapshot_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): snapshot_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [snapshot_value(item) for item in value]
    return value


@dataclass(frozen=True)
class TransformerAnalysisRequest:
    values: dict[str, Any]
    as_of: date = field(default_factory=date.today)
    standard_code: str = STANDARD_CODE


@dataclass(frozen=True)
class TransformerAnalysisResult:
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
    support_status: str = "SUPPORTED"
    reason_codes: tuple[str, ...] = ()

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
class TransformerAnalysisOutcome:
    result: TransformerAnalysisResult
    record: RecordSnapshot | None
    record_status: str
    record_error: str = ""


class TransformerAnalysisService:
    """数据与计算器由装配层注入，不读取Excel/PDF或数据库。"""

    def __init__(self, pack: dict[str, Any], calculator, *, records=None,
                 pack_sha256: str = "", app_version: str = ""):
        self._pack = deepcopy(pack)
        self._calculator = calculator
        self._records = records
        self._pack_sha256 = pack_sha256
        self.app_version = app_version

    @property
    def input_contract(self):
        return get_transformer_input_contract()

    def evaluate(self, request: TransformerAnalysisRequest) -> TransformerAnalysisResult:
        if request.standard_code != STANDARD_CODE:
            raise ValueError("变压器请求标准与GB 20052—2024不一致")
        values = deepcopy(request.values)
        evaluated = self._calculator.evaluate(values, self._pack)
        # 领域状态在此投影到既有记录语义，不把执行异常转成业务无法判定。
        status = {"OUT_OF_SCOPE": "OUT_OF_STANDARD_SCOPE",
                  "UNABLE_TO_JUDGE": "INSUFFICIENT_DATA"}.get(
                      evaluated.evaluation_status, evaluated.evaluation_status)
        references = {
            "standard_code": STANDARD_CODE,
            "standard_year": "2024",
            "canonical_version": self._pack.get("mapping_revision", "V2.1"),
            "canonical_package_hash": self._pack_sha256,
            "calculator_version": getattr(self._calculator, "calculator_id", ""),
            "numeric_profile_id": NUMERIC_PROFILE,
            "result_contract_version": "transformer-result.v1",
            "source_identity": deepcopy(self._pack.get("source_files", {})),
        }
        raw_category = str(values.get("category") or values.get("category_id") or "")
        category_label = next((item.label for item in self.input_contract.categories
                               if raw_category in (item.category_id, item.label)), raw_category)
        return TransformerAnalysisResult(
            product_category=category_label,
            as_of=request.as_of, evaluation_status=status,
            grade=evaluated.grade, ui_conclusion=evaluated.ui_conclusion,
            thresholds=dict(evaluated.thresholds),
            explanation=evaluated.explanation,
            missing_fields=tuple(evaluated.missing_fields),
            trace=snapshot_value(evaluated.trace), raw_values=snapshot_value(values),
            references=references, reason_codes=tuple(getattr(evaluated, "reason_codes", ())))

    def standard_overview(self) -> dict[str, Any]:
        return {
            "standard_code": STANDARD_CODE,
            "name": self._pack.get("standard_name", "电力变压器能效限定值及能效等级"),
            "edition": "2024",
            "effective_date": self._pack.get("effective_date", ""),
            "support_status": "SUPPORTED",
            "scope_text": "按GB 20052—2024适用型式选择类别，包含普通与新能源变压器。",
            "notes": "本版本正式支持GB 20052-2024适用型式。",
        }

    def analyze_and_record(self, request: TransformerAnalysisRequest) -> TransformerAnalysisOutcome:
        result = self.evaluate(request)
        if not result.finalizable:
            return TransformerAnalysisOutcome(result, None, "NOT_ELIGIBLE")
        if self._records is None:
            return TransformerAnalysisOutcome(result, None, "SAVE_FAILED", "未装配历史记录存储")
        now = datetime.now(timezone.utc).isoformat()
        references = result.references
        inputs = deepcopy(result.raw_values)
        inputs["request_fingerprint"] = stable_fingerprint(
            inputs | {"standard_code": STANDARD_CODE, "as_of": request.as_of.isoformat()})
        record = RecordSnapshot(
            record_id=f"TR-{uuid4().hex}", workspace_id=None,
            standard_code=STANDARD_CODE, standard_version="2024",
            device_type="transformer", product_category=result.product_category,
            rule_profile="transformer", as_of=request.as_of.isoformat(),
            evaluation_status=str(result.evaluation_status), grade=result.grade,
            ui_conclusion=result.ui_conclusion, input_snapshot=inputs,
            result_snapshot=result.as_snapshot(), reference_snapshot=deepcopy(references),
            ruleset_version="GB20052-V2.1", calculator_version=references["calculator_version"],
            numeric_profile_id=NUMERIC_PROFILE,
            canonical_version=references["canonical_version"],
            canonical_package_hash=self._pack_sha256,
            result_contract_version=references["result_contract_version"],
            schema_version=1, created_at_utc=now, finalized_at_utc=now)
        try:
            self._records.append_record(record)
        except Exception as error:
            return TransformerAnalysisOutcome(
                result, None, "SAVE_FAILED", f"{type(error).__name__}: {error}")
        return TransformerAnalysisOutcome(result, record, "SAVED")
