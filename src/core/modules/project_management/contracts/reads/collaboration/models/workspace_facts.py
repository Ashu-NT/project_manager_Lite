from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.core.platform.domain.master_data.documents import (
    DocumentStorageKind,
    DocumentType,
)


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
    is_deleted: bool = False
    deleted_at: datetime | None = None


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
class CollaborationCommentCriteria:
    project_id: str | None = None
    author_username: str | None = None
    search_text: str = ""
    created_since: datetime | None = None
    mention_aliases: tuple[str, ...] = ()
    principal_user_id: str | None = None
    principal_mentions_only: bool = False
    unread_only: bool = False


@dataclass(frozen=True, slots=True)
class CollaborationCommentReadPage:
    items: tuple[CollaborationCommentFact, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True, slots=True)
class TaskDetailCommentFact:
    id: str
    task_id: str
    author_user_id: str | None
    author_username: str | None
    body: str
    mentions: tuple[str, ...]
    attachments: tuple[str, ...]
    created_at: datetime
    parent_comment_id: str | None
    parent_author_username: str
    reply_count: int
    updated_at: datetime | None
    deleted_at: datetime | None
    deletion_reason: str | None
    reactions: tuple[tuple[str, tuple[str, ...]], ...]
    version: int


@dataclass(frozen=True, slots=True)
class TaskDetailCommentReadPage:
    items: tuple[TaskDetailCommentFact, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True, slots=True)
class TaskDocumentOptionFact:
    id: str
    document_code: str
    title: str


@dataclass(frozen=True, slots=True)
class TaskDetailLinkedDocumentFact:
    id: str
    file_name: str | None
    title: str
    document_code: str
    document_type: DocumentType
    storage_kind: DocumentStorageKind


__all__ = [
    name for name in globals()
    if name.startswith(("Collaboration", "TaskDetail", "TaskDocument"))
]
