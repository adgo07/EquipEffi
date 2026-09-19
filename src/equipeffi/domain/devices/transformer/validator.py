from typing import Any

from ...common.issues import ValidationIssue


class TransformerValidator:
    """变压器领域校验入口。"""

    def validate(self, values: dict[str, Any]) -> list[ValidationIssue]:
        return []
