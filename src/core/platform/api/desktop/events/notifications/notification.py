from __future__ import annotations

from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.events.notifications.models.notification import NotificationDto
from src.core.platform.application.events.notifications.notification_service import NotificationService
from src.core.platform.domain.events.notifications import Notification


class PlatformNotificationDesktopApi:
    """Desktop-facing adapter for the current principal's in-app notifications."""

    def __init__(self, *, notification_service: NotificationService) -> None:
        self._notification_service = notification_service

    def list_my_notifications(
        self,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> DesktopApiResult[tuple[NotificationDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize(notification)
                for notification in self._notification_service.list_my_notifications(
                    unread_only=unread_only,
                    limit=limit,
                )
            )
        )

    def count_my_unread(self) -> DesktopApiResult[int]:
        return execute_desktop_operation(self._notification_service.count_my_unread)

    def mark_read(self, notification_id: str) -> DesktopApiResult[NotificationDto]:
        return execute_desktop_operation(
            lambda: self._serialize(self._notification_service.mark_read(notification_id))
        )

    def mark_all_read(self) -> DesktopApiResult[int]:
        return execute_desktop_operation(self._notification_service.mark_all_read)

    @staticmethod
    def _serialize(notification: Notification) -> NotificationDto:
        return NotificationDto(
            id=notification.id,
            category=notification.category,
            title=notification.title,
            body=notification.body,
            created_at=notification.created_at,
            read_at=notification.read_at,
            is_read=notification.is_read,
            metadata=dict(notification.metadata or {}),
        )


__all__ = ["PlatformNotificationDesktopApi"]
