from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ...domain.common.enums import EliminationScope
from ...domain.common.models import DeviceDraft, EvaluationResult
from ...domain.evaluation.device_types import PUBLIC_DEVICE_NAMES, PUBLIC_TYPE_BY_SHEET, profiles_for_public_type
from .input_normalization import DEVICE_ALIASES
from .batch_evaluation_service import BatchEvaluationService
from .evaluation_service import EvaluationService
from .v4_input_adapter import V4InputAdapter
from .v4_template_contract import V4TemplateContract
from .v4_validation import V4ValidationService


@dataclass(frozen=True)
class EvaluationRequest:
    """窗口、API和未来移动端共用的单台判定请求。"""

    record_id: str
    device_type: str
    values: dict[str, Any] = field(default_factory=dict)
    source: str = "manual"
    template_id: str = ""
    as_of: date | str = date(2026, 8, 23)


class EvaluationFacade:
    """把界面/HTTP/Excel输入统一接到现有判定服务。"""

    def __init__(self, evaluation_service: EvaluationService, contract: V4TemplateContract | None = None):
        self.evaluation_service = evaluation_service
        self.contract = contract

    def evaluate(
        self,
        request: EvaluationRequest,
        *,
        elimination_scope: EliminationScope = EliminationScope.MOTOR_BATCHES_1_4,
    ) -> EvaluationResult:
        metadata = {"input_source": request.source}
        if request.template_id:
            metadata["template_id"] = request.template_id
        draft = DeviceDraft(
            record_id=request.record_id,
            device_type=request.device_type,
            raw_values=dict(request.values),
            metadata=metadata,
        )
        result = self.evaluation_service.evaluate(draft, as_of=request.as_of, elimination_scope=elimination_scope)
        # 公共API同时接受15类代码和V4中文sheet名称；两者必须进入同一
        # V4ValidationService路径，否则中文调用会漏掉自动备注质量检查。
        public_type = PUBLIC_TYPE_BY_SHEET.get(str(request.device_type), str(request.device_type))
        sheet_name = PUBLIC_DEVICE_NAMES.get(public_type, "")
        if sheet_name:
            self._attach_quality_issues(result, sheet_name, request.values)
        return result

    def evaluate_v4(
        self,
        record_id: str,
        sheet_name: str,
        values: dict[str, Any],
        *,
        elimination_scope: EliminationScope = EliminationScope.MOTOR_BATCHES_1_4,
        as_of: date | str = date(2026, 8, 23),
    ) -> EvaluationResult:
        adapted = V4InputAdapter.adapt(record_id, sheet_name, values)
        result = self.evaluation_service.evaluate(adapted.draft, as_of=as_of, elimination_scope=elimination_scope)
        self._attach_quality_issues(result, sheet_name, values)
        return result

    def _attach_quality_issues(self, result: EvaluationResult, sheet_name: str, values: dict[str, Any]) -> None:
        enum_values: dict[str, set[str]] = {}
        if self.contract is not None:
            for field in self.contract.fields_for_sheet(sheet_name):
                if field.enum_name and self.contract.enums.get(field.enum_name):
                    enum_values[field.field_id] = set(self.contract.enums[field.enum_name])
        # 回退schema和直接公共API使用规范字段（如 ``rated_power_kw``），
        # 而V4自动备注规则沿用工作簿字段（如 ``rated_power``）。在只读副本
        # 中展开已登记的规范别名，保证两种入口获得同一质量检查；绝不改写
        # result或调用方传入的原始values。
        validation_values = self._validation_values(result, sheet_name, values)
        issues = V4ValidationService.validate(sheet_name, validation_values, enum_values=enum_values)
        result.data_quality_issues = [
            {"field": issue.field, "code": issue.code, "message": issue.message, "severity": issue.severity.value, "metadata": issue.metadata}
            for issue in issues
        ]
        for issue in issues:
            if issue.message not in result.notes:
                result.notes.append(issue.message)

    @staticmethod
    def _validation_values(result: EvaluationResult, sheet_name: str, values: dict[str, Any]) -> dict[str, Any]:
        expanded = dict(values)
        public_type = result.public_device_type or PUBLIC_TYPE_BY_SHEET.get(sheet_name, sheet_name)
        profiles = profiles_for_public_type(public_type) or (result.internal_device_type,)
        # DEVICE_ALIASES方向为“V4/兼容字段 -> 规范字段”；这里反向补入
        # V4质量检查使用的键，且只在原V4键不存在时补入，避免覆盖优先级。
        for profile in profiles:
            for alias, canonical in DEVICE_ALIASES.get(profile, {}).items():
                if canonical in expanded and alias not in expanded:
                    expanded[alias] = expanded[canonical]
        # 规范profile将电压明确标为V；V4电动机字段为kV。质量规则此处
        # 只检查正数/存在性，保留数值本身不会造成单位换算误判。
        if "rated_voltage_v" in expanded and "rated_voltage" not in expanded:
            expanded["rated_voltage"] = expanded["rated_voltage_v"]
        return expanded

    @staticmethod
    def to_record(result: EvaluationResult) -> dict[str, Any]:
        return BatchEvaluationService.result_record(result)
