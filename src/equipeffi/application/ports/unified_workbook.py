"""多设备工作簿载体契约；按Sheet和行共同定位，不包含Excel对象。"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .batch_workbook import BatchRowOutcome, BatchSourceWorkbook


@dataclass(frozen=True)
class UnifiedSourceWorkbook:
    path: str
    sheets: dict[str, BatchSourceWorkbook]
    template_identity: dict[str, str] = field(default_factory=dict)
    unprocessed_sheets: tuple[str, ...] = ()


class UnifiedWorkbookReader(Protocol):
    def read(self, source: Path) -> UnifiedSourceWorkbook: ...


class UnifiedResultWriter(Protocol):
    def default_destination(self, source: Path) -> Path: ...

    def write(self, source: Path,
              outcomes_by_sheet: dict[str, dict[int, BatchRowOutcome]],
              destination: Path, *, overwrite: bool = False) -> Path: ...
