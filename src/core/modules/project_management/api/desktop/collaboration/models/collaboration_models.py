"""Collaboration desktop DTOs, snapshot models, and descriptor models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CollaborationNotificationDesktopDto:
    entity_id: str
    notification_type: str
    notification_type_label: str
    entity_type: str
    headline: str
    body_preview: str
    actor_username: str
    created_at: datetime
    created_at_label: str
    project_id: str | None
    project_name: str
    attention: bool


@dataclass(frozen=True)
class CollaborationInboxDesktopDto:
    comment_id: str
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    author_username: str
    body_preview: str
    mentions: tuple[str, ...]
    mentions_label: str
    created_at: datetime
    created_at_label: str
    unread: bool


@dataclass(frozen=True)
class CollaborationPresenceDesktopDto:
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    username: str
    display_name: str | None
    activity: str
    activity_label: str
    who_label: str
    last_seen_at: datetime
    last_seen_at_label: str
    is_self: bool


@dataclass(frozen=True)
class TaskCollaborationMentionOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskCollaborationDocumentOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskCollaborationReactionSummaryDto:
    emoji: str
    count: int
    reactor_user_ids: tuple[str, ...]
    reacted_by_current_user: bool = False


@dataclass(frozen=True)
class TaskCollaborationCommentDesktopDto:
    comment_id: str
    task_id: str
    author_username: str
    body: str
    mentions: tuple[str, ...]
    mentions_label: str
    attachments: tuple[str, ...]
    attachments_label: str
    linked_documents: tuple[str, ...]
    linked_documents_label: str
    created_at: datetime
    created_at_label: str
    author_user_id: str | None = None
    parent_comment_id: str | None = None
    is_reply: bool = False
    updated_at: datetime | None = None
    updated_at_label: str = ""
    is_edited: bool = False
    is_deleted: bool = False
    reactions: tuple[TaskCollaborationReactionSummaryDto, ...] = ()
    reactions_label: str = ""
    parent_author_username: str = ""
    thread_depth: int = 0
    reply_count: int = 0
    can_reply: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_react: bool = False


@dataclass(frozen=True)
class TaskCollaborationSnapshotDto:
    comments: tuple[TaskCollaborationCommentDesktopDto, ...]
    active_presence: tuple[CollaborationPresenceDesktopDto, ...]
    mention_options: tuple[TaskCollaborationMentionOptionDescriptor, ...]
    document_options: tuple[TaskCollaborationDocumentOptionDescriptor, ...]


@dataclass(frozen=True)
class CollaborationWorkspaceSnapshotDto:
    notifications: tuple[CollaborationNotificationDesktopDto, ...]
    inbox: tuple[CollaborationInboxDesktopDto, ...]
    recent_activity: tuple[CollaborationInboxDesktopDto, ...]
    active_presence: tuple[CollaborationPresenceDesktopDto, ...]


__all__ = [
    "CollaborationInboxDesktopDto",
    "CollaborationNotificationDesktopDto",
    "CollaborationPresenceDesktopDto",
    "CollaborationWorkspaceSnapshotDto",
    "TaskCollaborationCommentDesktopDto",
    "TaskCollaborationDocumentOptionDescriptor",
    "TaskCollaborationMentionOptionDescriptor",
    "TaskCollaborationReactionSummaryDto",
    "TaskCollaborationSnapshotDto",
]
