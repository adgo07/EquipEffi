"""批量评价的载体端口（Phase 8）。

依赖方向铁律（`tests/contract/test_architecture_boundaries.py` 强制）：
**Application 不得 import Infrastructure / Excel**。因此批量评价对"读输入工作簿"
与"写结果工作簿"的需求只在这里声明为 Protocol，由 Infrastructure 实现、
由 composition 装配注入。

这与既有 `application/lifecycle/ports.py` 的做法一致：Application 认识契约，
不认识 SQLite / openpyxl。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class BatchSourceRow:
    """工作簿里的一行输入（只含正式输入字段）。"""

    row_number: int
    values: dict[str, Any]


@dataclass(frozen=True)
class BatchSourceWorkbook:
    """一次批量评价的输入载体。"""

    path: str
    rows: tuple[BatchSourceRow, ...]
    skipped_blank_rows: int = 0


@dataclass
class BatchRowOutcome:
    """单行评价结果（写回与批次汇总的唯一来源）。

    刻意放在 Application：它是"业务结果投影"，不是 Excel 概念。
    """

    row_number: int
    evaluated: bool
    conclusion: str
    evaluation_status: str | None
    grade: str | None
    messages: tuple[str, ...] = ()
    derived: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"row": self.row_number, "evaluated": self.evaluated,
                "conclusion": self.conclusion,
                "evaluation_status": self.evaluation_status,
                "grade": self.grade, "messages": list(self.messages)}


class BatchWorkbookReader(Protocol):
    """读取批量输入工作簿的端口。"""

    def read(self, source: Path) -> BatchSourceWorkbook: ...


class BatchResultWriter(Protocol):
    """写出结果工作簿的端口；实现方**必须**写入新文件，绝不覆盖输入。"""

    def write(self, source: Path, outcomes: dict[int, BatchRowOutcome],
              destination: Path) -> Path: ...
