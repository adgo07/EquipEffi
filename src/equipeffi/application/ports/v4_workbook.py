from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence

from ...domain.common.models import EvaluationResult


@dataclass(frozen=True)
class V4WorkbookRow:
    record_id: str
    sheet_name: str
    values: dict[str, Any] = field(default_factory=dict)
    row_number: int = 0


@dataclass(frozen=True)
class V4WorkbookEvaluationRow:
    row: V4WorkbookRow
    result: EvaluationResult


class V4WorkbookReader(Protocol):
    """V4读取器端口；实现可以是OOXML、桌面Excel或服务端解析器。"""

    def read_rows(self, source: Path) -> Sequence[V4WorkbookRow]: ...

    def read_settings(self, source: Path) -> dict[str, Any]: ...


class V4WorkbookWriter(Protocol):
    """V4结果写回端口；实现必须输出新文件，不覆盖输入文件。"""

    def write_results(self, source: Path, destination: Path, evaluations: Sequence[V4WorkbookEvaluationRow]) -> Path: ...
