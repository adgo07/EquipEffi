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

    `quantity` 是该行的「数量」（台），用于**数量加权**的批次汇总。
    `thresholds` 是当时的等级限值（关键限值），写回结果 Workbook。
    `is_input_error` / `is_execution_error` 把"输入问题"与"系统执行失败"
    与**正式评价结论**严格区分开：它们都不属于正式评价结论。
    """

    row_number: int
    evaluated: bool
    conclusion: str
    evaluation_status: str | None
    grade: str | None
    messages: tuple[str, ...] = ()
    derived: dict[str, Any] = field(default_factory=dict)
    thresholds: dict[str, Any] = field(default_factory=dict)
    quantity: int = 0
    is_input_error: bool = False
    is_execution_error: bool = False

    def as_dict(self) -> dict:
        return {"row": self.row_number, "evaluated": self.evaluated,
                "conclusion": self.conclusion,
                "evaluation_status": self.evaluation_status,
                "grade": self.grade, "quantity": self.quantity,
                "is_input_error": self.is_input_error,
                "is_execution_error": self.is_execution_error,
                "messages": list(self.messages)}


class BatchWorkbookReader(Protocol):
    """读取批量输入工作簿的端口。"""

    def read(self, source: Path) -> BatchSourceWorkbook: ...


class BatchResultWriter(Protocol):
    """写出结果工作簿的端口；实现方**必须**写入新文件，绝不覆盖输入。

    目标文件已存在时实现方**不得静默覆盖**。
    """

    def default_destination(self, source: Path) -> Path:
        """默认结果文件路径（实现方负责命名约定，例如带时间戳）。"""

    def write(self, source: Path, outcomes: dict[int, BatchRowOutcome],
              destination: Path, *, overwrite: bool = False) -> Path: ...


class BatchTemplateResource(Protocol):
    """正式空白模板资源端口（供"输出空白模板"一次操作使用）。

    实现方负责把**入仓的正式模板**复制到用户选择的位置；
    Presentation 因此不必（也不得）import Infrastructure。
    """

    def download_to(self, destination: Path) -> Path: ...
