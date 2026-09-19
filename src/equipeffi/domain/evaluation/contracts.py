from typing import Any, Protocol

from ..common.models import EvaluationResult


class IndicatorCalculator(Protocol):
    def calculate(self, values: dict[str, Any]) -> dict[str, Any]: ...


class Evaluator(Protocol):
    def evaluate(
        self,
        values: dict[str, Any],
        *args: dict[str, Any],
    ) -> EvaluationResult: ...
