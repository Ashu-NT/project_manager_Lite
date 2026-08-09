from __future__ import annotations

from typing import Protocol

from .models import TaskWorkspaceCriteria, TaskWorkspaceReadPage


class TaskWorkspaceReader(Protocol):
    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        criteria: TaskWorkspaceCriteria,
        page: int,
        page_size: int,
    ) -> TaskWorkspaceReadPage: ...


__all__ = ["TaskWorkspaceReader"]
