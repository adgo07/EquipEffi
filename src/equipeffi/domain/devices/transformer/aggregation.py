from typing import Any


class TransformerAggregation:
    """变压器汇总字段定义入口。"""

    def aggregate(self, values: dict[str, Any]) -> dict[str, Any]:
        return {
            "quantity": values.get("quantity"),
            "capacity_kva": values.get("capacity_kva"),
        }
