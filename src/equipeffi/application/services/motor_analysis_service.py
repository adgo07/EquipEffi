"""GB 18613-2020 application contract shared by the product adapters."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from ...domain.devices.motor.input_contract import (
    MOTOR_CATEGORIES, MOTOR_INPUT_CONTRACT, MotorInputError, normalize_motor_input
)
from ..lifecycle import RecordSnapshot, stable_fingerprint


STANDARD_CODE = "GB 18613-2020"

def get_motor_input_contract():
    """Return the shared GB 18613 input contract for Application consumers."""
    return MOTOR_INPUT_CONTRACT


NUMERIC_PROFILE = "EQUIPEFFI_MOTOR_EXACT_LINEAR_V1"
RESULT_CONTRACT_VERSION = "motor-result.v1"
RULE_PROFILE = "motor_lv"
_THRESHOLD_KEYS = ("grade_1", "grade_2", "grade_3")


def snapshot_value(value: Any) -> Any:
    """Convert exact numeric values to JSON-safe text without float coercion."""
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        return {item.name: snapshot_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): snapshot_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [snapshot_value(item) for item in value]
    return value


def _threshold_display_projection(thresholds: Mapping[str, Any]) -> dict[str, str | None]:
    """Project threshold records for Qt/Workbook while retaining exact data separately."""
    projected: dict[str, str | None] = {}
    for key in _THRESHOLD_KEYS:
        threshold = thresholds.get(key)
        if not isinstance(threshold, Mapping):
            projected[key] = None
        elif threshold.get("state") == "NO_INDICATOR":
            projected[key] = "—"
        elif threshold.get("state") == "AVAILABLE":
            display = threshold.get("display_text")
            projected[key] = str(display) if display not in (None, "") else None
        else:
            # A missing precondition is not equivalent to a standard dash.
            projected[key] = None
    return projected


@dataclass(frozen=True)
class MotorAnalysisRequest:
    values: dict[str, Any]
    as_of: date = field(default_factory=date.today)
    standard_code: str = STANDARD_CODE


@dataclass(frozen=True)
class MotorAnalysisResult:
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
class MotorAnalysisOutcome:
    result: MotorAnalysisResult
    record: RecordSnapshot | None
    record_status: str
    record_error: str = ""


class MotorAnalysisService:
    """Injects the GB18613 pack/calculator and persists only legal results."""

    def __init__(self, pack: Mapping[str, Any], calculator: Any, *, records=None,
                 pack_sha256: str = "", app_version: str = ""):
        self._pack = deepcopy(dict(pack))
        self._calculator = calculator
        self._records = records
        self._pack_sha256 = pack_sha256
        self.app_version = app_version

    @property
    def input_contract(self):
        return MOTOR_INPUT_CONTRACT

    def evaluate(self, request: MotorAnalysisRequest) -> MotorAnalysisResult:
        if request.standard_code != STANDARD_CODE:
            raise ValueError("电动机请求标准与GB 18613-2020不一致")
        values = deepcopy(request.values)
        evaluated = self._calculator.evaluate(values, self._pack)
        exact_thresholds = deepcopy(dict(evaluated.thresholds))
        snapshot_values = values
        if evaluated.evaluation_status != "INVALID_INPUT":
            try:
                snapshot_values = normalize_motor_input(values)
            except MotorInputError as error:
                raise RuntimeError("Calculator与Application输入契约不一致") from error
        raw_category = snapshot_values.get("category_id", snapshot_values.get("category", ""))
        raw_category = "" if raw_category is None else str(raw_category)
        category = next(
            (item for item in MOTOR_CATEGORIES
             if raw_category in (item.category_id, item.label)), None)
        references = {
            "standard_code": STANDARD_CODE,
            "standard_year": "2020",
            "pack_id": self._pack.get("pack_id", "gb18613_2020_v2"),
            "canonical_version": self._pack.get("mapping_revision", "A.2"),
            "canonical_package_hash": self._pack_sha256,
            "calculator_version": getattr(
                self._calculator, "calculator_version",
                getattr(self._calculator, "calculator_id", "")),
            "numeric_profile_id": getattr(
                self._calculator, "numeric_profile_id", NUMERIC_PROFILE),
            "result_contract_version": RESULT_CONTRACT_VERSION,
            "source_identity": deepcopy(self._pack.get("source_files", {})),
        }
        calculated_references = snapshot_value(getattr(evaluated, "references", {}) or {})
        # Preserve the Application's verified package and calculator identity.
        references.update({
            key: value for key, value in calculated_references.items()
            if key not in references
        })
        return MotorAnalysisResult(
            product_category=category.label if category else raw_category,
            as_of=request.as_of,
            evaluation_status=evaluated.evaluation_status,
            grade=evaluated.grade,
            ui_conclusion=evaluated.ui_conclusion,
            thresholds=snapshot_value(exact_thresholds),
            explanation=evaluated.explanation,
            missing_fields=tuple(evaluated.missing_fields),
            trace=snapshot_value(evaluated.trace),
            raw_values=snapshot_value(snapshot_values),
            references=references,
            reason_codes=tuple(getattr(evaluated, "reason_codes", ())),
            invalid_fields=tuple(getattr(evaluated, "invalid_fields", ())),
        )

    def standard_overview(self) -> dict[str, Any]:
        return {
            "standard_code": STANDARD_CODE,
            "name": self._pack.get("standard_name", "电动机能效限定值及能效等级"),
            "edition": "2020",
            "effective_date": self._pack.get("effective_date", "2021-06-01"),
            "support_status": "IMPLEMENTED",
            "scope_text": "按GB 18613-2020规定的电动机类别评价表1至表6。",
            "notes": "已接入本版实现；正式支持状态以独立验收结论为准。",
        }

    def analyze_and_record(self, request: MotorAnalysisRequest) -> MotorAnalysisOutcome:
        result = self.evaluate(request)
        if not result.finalizable:
            return MotorAnalysisOutcome(result, None, "NOT_ELIGIBLE")
        if self._records is None:
            return MotorAnalysisOutcome(result, None, "SAVE_FAILED", "未装配历史记录存储")
        now = datetime.now(timezone.utc).isoformat()
        references = result.references
        inputs = deepcopy(result.raw_values)
        inputs["request_fingerprint"] = stable_fingerprint(
            inputs | {"standard_code": STANDARD_CODE, "as_of": request.as_of.isoformat()})
        record = RecordSnapshot(
            record_id=f"MO-{uuid4().hex}", workspace_id=None,
            standard_code=STANDARD_CODE, standard_version="2020",
            device_type=RULE_PROFILE, product_category=result.product_category,
            rule_profile=RULE_PROFILE, as_of=request.as_of.isoformat(),
            evaluation_status=str(result.evaluation_status), grade=result.grade,
            ui_conclusion=result.ui_conclusion, input_snapshot=inputs,
            result_snapshot=result.as_snapshot(), reference_snapshot=deepcopy(references),
            ruleset_version=str(self._pack.get("mapping_revision", "GB18613-A.2")),
            calculator_version=str(references["calculator_version"]),
            numeric_profile_id=str(references["numeric_profile_id"]),
            canonical_version=str(references["canonical_version"]),
            canonical_package_hash=self._pack_sha256,
            result_contract_version=RESULT_CONTRACT_VERSION,
            schema_version=1, created_at_utc=now, finalized_at_utc=now)
        try:
            self._records.append_record(record)
        except Exception as error:
            return MotorAnalysisOutcome(
                result, None, "SAVE_FAILED", f"{type(error).__name__}: {error}")
        return MotorAnalysisOutcome(result, record, "SAVED")
