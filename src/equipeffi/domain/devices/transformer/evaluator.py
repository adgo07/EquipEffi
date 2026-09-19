from typing import Any

from ...common.enums import Conclusion
from ...common.models import EvaluationResult


class TransformerEvaluator:
    """变压器评价入口；具体查表和比较逻辑后续从旧实现迁移。"""

    def evaluate(
        self,
        values: dict[str, Any],
        indicators: dict[str, Any],
        standard: dict[str, Any],
    ) -> EvaluationResult:
        return EvaluationResult(
            record_id=str(values.get("record_id", "")),
            conclusion=Conclusion.UNABLE_TO_JUDGE,
            notes=["新领域评价器尚未接入旧判定逻辑"],
        )
