"""设备无关的生命周期端口（Phase 4 G01）。

持久化只能经这里的 Protocol 进入；生命周期层与具体产品模块都不认识 SQLite。

实现方（infrastructure）只允许依赖本模块的 models / errors，
**不得**依赖任何 `*_analysis_service` 产品模块——该约束由
`tests/contract/test_architecture_boundaries.py` 的架构门禁强制。
"""
from __future__ import annotations

from typing import Protocol

from .models import RecordSnapshot, WorkspaceSnapshot


class WorkspaceRepository(Protocol):
    """可变草稿仓储。"""

    def save_workspace(self, snapshot: WorkspaceSnapshot) -> None: ...
    def load_workspace(self, workspace_id: str) -> WorkspaceSnapshot | None: ...
    def list_workspaces(self, limit: int = 50) -> list[WorkspaceSnapshot]: ...
    def delete_workspace(self, workspace_id: str) -> None: ...


class RecordRepository(Protocol):
    """不可变正式记录仓储：只追加，不提供 update / delete。"""

    def append_record(self, snapshot: RecordSnapshot) -> None: ...
    def load_record(self, record_id: str) -> RecordSnapshot | None: ...
    def list_records(self, limit: int = 200) -> list[RecordSnapshot]: ...
