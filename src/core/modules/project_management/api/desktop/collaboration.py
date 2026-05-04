from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.core.modules.project_management.application.tasks import CollaborationService


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
class CollaborationWorkspaceSnapshotDto:
    notifications: tuple[CollaborationNotificationDesktopDto, ...]
    inbox: tuple[CollaborationInboxDesktopDto, ...]
    recent_activity: tuple[CollaborationInboxDesktopDto, ...]
    active_presence: tuple[CollaborationPresenceDesktopDto, ...]


class ProjectManagementCollaborationDesktopApi:
    def __init__(
        self,
        *,
        collaboration_service: CollaborationService | None = None,
    ) -> None:
        self._collaboration_service = collaboration_service

    def build_snapshot(self, *, limit: int = 200) -> CollaborationWorkspaceSnapshotDto:
        if self._collaboration_service is None:
            return CollaborationWorkspaceSnapshotDto(
                notifications=(),
                inbox=(),
                recent_activity=(),
                active_presence=(),
            )
        snapshot = self._collaboration_service.list_workspace_snapshot(limit=limit)
        return CollaborationWorkspaceSnapshotDto(
            notifications=tuple(
                self._serialize_notification(item) for item in snapshot.notifications
            ),
            inbox=tuple(self._serialize_inbox_item(item) for item in snapshot.inbox),
            recent_activity=tuple(
                self._serialize_inbox_item(item) for item in snapshot.recent_activity
            ),
            active_presence=tuple(
                self._serialize_presence_item(item)
                for item in snapshot.active_presence
            ),
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("Task ID is required to mark collaboration mentions as read.")
        self._require_collaboration_service().mark_task_mentions_read(normalized_task_id)

    def _require_collaboration_service(self) -> CollaborationService:
        if self._collaboration_service is None:
            raise RuntimeError(
                "Project management collaboration desktop API is not connected."
            )
        return self._collaboration_service

    @staticmethod
    def _serialize_notification(item) -> CollaborationNotificationDesktopDto:
        return CollaborationNotificationDesktopDto(
            entity_id=item.entity_id,
            notification_type=item.notification_type,
            notification_type_label=_format_enum_label(item.notification_type),
            entity_type=item.entity_type,
            headline=item.headline,
            body_preview=item.body_preview,
            actor_username=item.actor_username,
            created_at=item.created_at,
            created_at_label=_format_datetime(item.created_at),
            project_id=item.project_id,
            project_name=item.project_name or "",
            attention=bool(item.attention),
        )

    @staticmethod
    def _serialize_inbox_item(item) -> CollaborationInboxDesktopDto:
        mentions = tuple(str(mention).strip() for mention in item.mentions if str(mention).strip())
        return CollaborationInboxDesktopDto(
            comment_id=item.comment_id,
            task_id=item.task_id,
            task_name=item.task_name,
            project_id=item.project_id,
            project_name=item.project_name,
            author_username=item.author_username,
            body_preview=item.body_preview,
            mentions=mentions,
            mentions_label=", ".join(f"@{mention}" for mention in mentions) if mentions else "No direct mentions",
            created_at=item.created_at,
            created_at_label=_format_datetime(item.created_at),
            unread=bool(item.unread),
        )

    @staticmethod
    def _serialize_presence_item(item) -> CollaborationPresenceDesktopDto:
        display_name = (item.display_name or "").strip() or None
        username = (item.username or "").strip()
        if display_name and username:
            who_label = f"{display_name} (@{username})"
        elif display_name:
            who_label = display_name
        else:
            who_label = f"@{username}" if username else "Unknown"
        return CollaborationPresenceDesktopDto(
            task_id=item.task_id,
            task_name=item.task_name,
            project_id=item.project_id,
            project_name=item.project_name,
            username=username,
            display_name=display_name,
            activity=item.activity,
            activity_label=_format_enum_label(item.activity),
            who_label=who_label,
            last_seen_at=item.last_seen_at,
            last_seen_at_label=_format_datetime(item.last_seen_at),
            is_self=bool(item.is_self),
        )


def build_project_management_collaboration_desktop_api(
    *,
    collaboration_service: CollaborationService | None = None,
) -> ProjectManagementCollaborationDesktopApi:
    return ProjectManagementCollaborationDesktopApi(
        collaboration_service=collaboration_service,
    )


def _format_enum_label(value: str) -> str:
    return str(value or "").replace("_", " ").title()


def _format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


__all__ = [
    "CollaborationInboxDesktopDto",
    "CollaborationNotificationDesktopDto",
    "CollaborationPresenceDesktopDto",
    "CollaborationWorkspaceSnapshotDto",
    "ProjectManagementCollaborationDesktopApi",
    "build_project_management_collaboration_desktop_api",
]
