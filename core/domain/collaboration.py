from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from core.domain.identifiers import generate_id


@dataclass
class TaskComment:
    id: str
    task_id: str
    author_user_id: str | None
    author_username: str | None
    body: str
    mentions: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    read_by: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
        task_id: str,
        author_user_id: str | None,
        author_username: str | None,
        body: str,
        mentions: Iterable[str] | None = None,
        attachments: Iterable[str] | None = None,
        read_by: Iterable[str] | None = None,
    ) -> "TaskComment":
        return TaskComment(
            id=generate_id(),
            task_id=task_id,
            author_user_id=author_user_id,
            author_username=author_username,
            body=(body or "").strip(),
            mentions=sorted({str(item).strip().lower() for item in (mentions or []) if str(item).strip()}),
            attachments=[str(item).strip() for item in (attachments or []) if str(item).strip()],
            read_by=sorted({str(item).strip().lower() for item in (read_by or []) if str(item).strip()}),
        )


@dataclass
class CollaborationInboxItem:
    comment_id: str
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    author_username: str
    body_preview: str
    mentions: list[str]
    created_at: datetime
    unread: bool = True


__all__ = ["TaskComment", "CollaborationInboxItem"]
