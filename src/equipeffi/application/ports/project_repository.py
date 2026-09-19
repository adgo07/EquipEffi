from typing import Protocol

from ...domain.common.models import DeviceDraft


class ProjectRepository(Protocol):
    def save_draft(self, project_id: str, draft: DeviceDraft) -> None: ...

    def list_drafts(self, project_id: str) -> list[DeviceDraft]: ...
