from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping


@dataclass
class TransformerInput:
    record_id: str
    model: str | None = None
    category: str | None = None
    quantity: int | None = None
    capacity_kva: float | None = None
    core_material: str | None = None
    insulation: str | None = None
    connection: str | None = None
    no_load_loss_w: float | None = None
    load_loss_w: float | None = None
    extra: dict[str, Any] | None = None


@dataclass(frozen=True)
class TransformerEvaluation:
    """Stable Domain result returned by the GB 20052 transformer calculator."""

    evaluation_status: str | None
    grade: str | None
    ui_conclusion: str
    thresholds: Mapping[str, Decimal] = field(default_factory=dict)
    explanation: str = ""
    missing_fields: tuple[str, ...] = ()
    trace: tuple[Mapping[str, Any], ...] = ()
    reason_codes: tuple[str, ...] = ()
