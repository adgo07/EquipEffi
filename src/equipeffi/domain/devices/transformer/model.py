from dataclasses import dataclass
from typing import Any


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
