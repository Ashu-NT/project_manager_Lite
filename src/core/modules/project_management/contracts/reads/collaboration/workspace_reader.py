from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .models.workspace_facts import CollaborationWorkspaceFacts


class CollaborationWorkspaceReader(Protocol):
    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        accessible_project_ids: tuple[str, ...],
        comment_limit: int,
        presence_since: datetime | None = None,
        presence_limit: int = 0,
    ) -> CollaborationWorkspaceFacts: ...


__all__ = ["CollaborationWorkspaceReader"]
