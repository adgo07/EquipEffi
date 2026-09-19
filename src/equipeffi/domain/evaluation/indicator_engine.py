from typing import Any

from .contracts import IndicatorCalculator


class IndicatorEngine:
    """统一调度设备的输入指标计算。

    具体公式由设备模块提供；本类不包含设备专用逻辑。
    """

    def calculate(
        self,
        calculator: IndicatorCalculator,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        return calculator.calculate(values)
