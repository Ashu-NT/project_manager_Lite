from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .models.workspace_facts import (
    CollaborationCommentCriteria,
    CollaborationCommentReadPage,
    CollaborationPresenceFact,
)


class CollaborationWorkspaceReader(Protocol):
    def read_comment_authors(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        accessible_project_ids: tuple[str, ...],
    ) -> tuple[str, ...]: ...

    def read_comment_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        accessible_project_ids: tuple[str, ...],
        criteria: CollaborationCommentCriteria,
        page: int,
        page_size: int,
    ) -> CollaborationCommentReadPage: ...

    def read_active_presence(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        accessible_project_ids: tuple[str, ...],
        active_since: datetime,
    ) -> tuple[CollaborationPresenceFact, ...]: ...


__all__ = ["CollaborationWorkspaceReader"]
