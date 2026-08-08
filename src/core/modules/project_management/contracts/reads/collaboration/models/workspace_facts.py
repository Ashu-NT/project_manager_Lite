from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CollaborationCommentFact:
    comment_id: str
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    author_user_id: str | None
    author_username: str | None
    body: str
    mentions: tuple[str, ...]
    mentioned_user_ids: tuple[str, ...]
    read_by: tuple[str, ...]
    read_by_user_ids: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CollaborationPresenceFact:
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    user_id: str | None
    username: str
    display_name: str | None
    activity: str
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class CollaborationWorkspaceFacts:
    tenant_id: str
    organization_id: str
    comments: tuple[CollaborationCommentFact, ...]
    active_presence: tuple[CollaborationPresenceFact, ...]


__all__ = [name for name in globals() if name.startswith("Collaboration")]
