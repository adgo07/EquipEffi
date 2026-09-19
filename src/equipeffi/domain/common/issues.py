from dataclasses import dataclass, field
from typing import Any

from .enums import IssueSeverity


@dataclass(frozen=True)
class ValidationIssue:
    field: str | None
    code: str
    message: str
    severity: IssueSeverity = IssueSeverity.WARNING
    metadata: dict[str, Any] = field(default_factory=dict)
