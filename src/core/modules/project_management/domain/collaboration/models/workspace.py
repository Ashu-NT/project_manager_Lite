from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


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


@dataclass(frozen=True, slots=True)
class CollaborationInboxPage:
    items: tuple[CollaborationInboxItem, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True)
class CollaborationContextOptions:
    projects: tuple[tuple[str, str], ...] = ()
    people: tuple[str, ...] = ()


__all__ = [
    "CollaborationContextOptions",
    "CollaborationInboxItem",
    "CollaborationInboxPage",
]
