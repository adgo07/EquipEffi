import inspect
from typing import Any

from ..common.models import EvaluationResult
from .contracts import Evaluator


class EvaluationEngine:
    """统一调度标准查询后的设备评价。

    当前设备评价器接收``(values, standard)``；早期插件契约曾使用
    ``(values, indicators, standard)``。引擎在边界处按可调用对象签名选择
    调用方式，使旧插件可以继续工作，同时避免用捕获 ``TypeError`` 的方式
    掩盖评价器内部真正的类型错误。
    """

    def evaluate(
        self,
        evaluator: Evaluator,
        values: dict[str, Any],
        indicators: dict[str, Any],
        standard: dict[str, Any],
    ) -> EvaluationResult:
        method = evaluator.evaluate
        try:
            parameters = tuple(inspect.signature(method).parameters.values())
        except (TypeError, ValueError):
            # 某些扩展实现可能没有可反射签名；按历史三参数契约调用。
            return method(values, indicators, standard)
        if any(parameter.kind is inspect.Parameter.VAR_POSITIONAL for parameter in parameters):
            return method(values, indicators, standard)
        positional = tuple(
            parameter
            for parameter in parameters
            if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        if len(positional) >= 3:
            return method(values, indicators, standard)
        return method(values, standard)
