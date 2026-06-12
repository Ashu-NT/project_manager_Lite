from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from src.core.modules.project_management.domain.collaboration.notifications.notification import CollaborationNotificationItem
from src.core.modules.project_management.domain.collaboration.presence.presence import TaskPresenceStatusItem


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


@dataclass(frozen=True)
class CollaborationWorkspaceSnapshot:
    notifications: list[CollaborationNotificationItem]
    inbox: list[CollaborationInboxItem]
    recent_activity: list[CollaborationInboxItem]
    active_presence: list[TaskPresenceStatusItem]


__all__ = ["CollaborationInboxItem", "CollaborationWorkspaceSnapshot"]
