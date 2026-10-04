from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
)

from .models.workspace_facts import (
    CollaborationCommentCriteria,
    CollaborationCommentReadPage,
    CollaborationPresenceFact,
    TaskDetailCommentReadPage,
    TaskDetailLinkedDocumentFact,
    TaskDocumentOptionFact,
)


class CollaborationWorkspaceReader(Protocol):
    def read_document_options(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        query: str = "",
        limit: int = 50,
    ) -> tuple[TaskDocumentOptionFact, ...]: ...

    def read_mention_candidates(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        query: str = "",
        handles: tuple[str, ...] = (),
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[CollaborationMentionCandidate, ...]: ...

    def read_task_comment_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        task_id: str,
        page: int,
        page_size: int,
    ) -> TaskDetailCommentReadPage: ...

    def read_task_comment_documents(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        task_id: str,
        comment_ids: tuple[str, ...],
    ) -> dict[str, tuple[TaskDetailLinkedDocumentFact, ...]]: ...

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
