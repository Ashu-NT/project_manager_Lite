from __future__ import annotations

from typing import Protocol

from .models import TaskWorkspaceCriteria, TaskWorkspaceReadPage
from src.core.modules.project_management.contracts.reads.sorting import ReadSort


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
        sort: ReadSort,
    ) -> TaskWorkspaceReadPage: ...


__all__ = ["TaskWorkspaceReader"]
