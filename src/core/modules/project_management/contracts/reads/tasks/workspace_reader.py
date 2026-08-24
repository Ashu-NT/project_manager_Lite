from __future__ import annotations

from typing import Protocol

from .models import (
    TaskActivityPage,
    TaskAssignmentReadPage,
    TaskDependencyReadPage,
    TaskWorkspaceCriteria,
    TaskWorkspaceReadPage,
)
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

    def read_assignments_page(
        self, *, tenant_id: str, organization_id: str, task_id: str,
        search_text: str, response_status: str | None, page: int,
        page_size: int, sort: ReadSort,
    ) -> TaskAssignmentReadPage: ...

    def read_dependencies_page(
        self, *, tenant_id: str, organization_id: str, task_id: str,
        search_text: str, direction: str, dependency_type: str | None,
        page: int, page_size: int, sort: ReadSort,
    ) -> TaskDependencyReadPage: ...

    def read_activity_page(
        self, *, tenant_id: str, organization_id: str, task_id: str,
        search_text: str, category: str, page: int, page_size: int,
    ) -> TaskActivityPage: ...


__all__ = ["TaskWorkspaceReader"]
