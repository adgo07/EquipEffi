from typing import Any


class TransformerIndicatorCalculator:
    """变压器指标计算入口。

    空载损耗和负载损耗本身就是实际比较指标，不在此处凭空增加派生指标。
    """

    def calculate(self, values: dict[str, Any]) -> dict[str, Any]:
        return {
            "no_load_loss_w": values.get("no_load_loss_w"),
            "load_loss_w": values.get("load_loss_w"),
        }
