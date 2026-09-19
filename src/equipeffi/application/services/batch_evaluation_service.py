from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any, Iterable

from ...domain.common.models import DeviceDraft, EvaluationResult
from .evaluation_service import EvaluationService


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return value


class BatchEvaluationService:
    """批量评价接口：Excel适配器只需把模板行映射为DeviceDraft即可复用。"""

    def __init__(self, evaluator: EvaluationService):
        self.evaluator = evaluator

    def evaluate(self, drafts: Iterable[DeviceDraft], **kwargs: Any) -> list[EvaluationResult]:
        return [self.evaluator.evaluate(draft, **kwargs) for draft in drafts]

    @staticmethod
    def result_record(result: EvaluationResult) -> dict[str, Any]:
        record = asdict(result)
        record["conclusion"] = result.conclusion.value
        record["reference_conclusion"] = result.reference_conclusion.value if result.reference_conclusion else ""
        record["elimination_scope"] = result.elimination_scope.value
        # T06公共结果契约使用简短的``elimination``键；保留已有的
        # ``elimination_match``字段，避免破坏旧调用方，同时让跨端消费
        # 者无需了解领域内部命名即可读取同一份结构化命中证据。
        record["elimination"] = record.get("elimination_match")
        # 判定轨迹是跨UI、HTTP、JSONL和未来移动端的公共数据结构。
        # 各专属评价器可以继续保留自己的细节字段；这里补齐稳定的序号和
        # 规则编号，避免适配器依赖中文步骤名称或自行推断步骤顺序。
        record["trace_schema_version"] = result.trace_schema_version or "1.0"
        record["trace"] = BatchEvaluationService._normalize_trace(result.trace)
        return _json_value(record)

    @staticmethod
    def _normalize_trace(trace: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        rule_prefixes = {
            "判定基准日期": "CORE.DATE",
            "输入规范化": "CORE.NORMALIZE",
            "V4工作表适配": "V4.ADAPT",
            "公共设备类型路由": "CORE.ROUTE",
            "淘汰检查": "ELIMINATION.MATCH",
            "范围检查": "SCOPE.CHECK",
            "输入校验": "INPUT.VALIDATE",
            "终止": "CORE.TERMINATE",
            "标准生效日期": "STANDARD.EFFECTIVE_DATE",
            "精确查表": "STANDARD.LOOKUP",
            "精确查表/区间查表": "STANDARD.LOOKUP",
            "线性插值": "STANDARD.INTERPOLATE",
            "功率线性插值": "STANDARD.INTERPOLATE",
            "转速线性插值": "STANDARD.INTERPOLATE",
            "标准查询结果": "STANDARD.LOOKUP_RESULT",
            "标准查表+公式计算": "STANDARD.LOOKUP_CALC",
            "公式计算": "STANDARD.CALC",
            "固定门槛": "STANDARD.GATE",
            "静压修正": "STANDARD.CORRECT",
            "等级比较": "GRADE.COMPARE",
        }
        normalized: list[dict[str, Any]] = []
        for sequence, original in enumerate(trace, start=1):
            step = dict(original)
            step_type = str(step.get("step_type", "未命名步骤"))
            step.setdefault("step_sequence", sequence)
            step.setdefault("rule_id", rule_prefixes.get(step_type, f"CUSTOM.{step_type}"))
            normalized.append(step)
        return normalized

    def evaluate_records(self, records: Iterable[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        drafts = [DeviceDraft(record_id=str(item["record_id"]), device_type=str(item["device_type"]), raw_values=dict(item.get("values", {}))) for item in records]
        return [self.result_record(result) for result in self.evaluate(drafts, **kwargs)]
