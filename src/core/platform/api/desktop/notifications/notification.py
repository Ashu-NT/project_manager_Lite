from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.application.notifications.commands import (
    NotificationCommandHandler,
)
from src.core.platform.application.notifications.dto.responses.notification import (
    NotificationDto,
)
from src.core.platform.application.notifications.queries import NotificationQueryHandler
from src.core.platform.contract.port.notifications.capabilities import (
    NotificationDeliveryRuntime,
)


class PlatformNotificationDesktopApi:
    """Desktop-facing adapter for the current principal's in-app notifications."""

    def __init__(self, *, notification_commands: NotificationCommandHandler, notification_queries: NotificationQueryHandler, notification_delivery: NotificationDeliveryRuntime) -> None:
        self._notification_commands = notification_commands
        self._notification_queries = notification_queries
        self._notification_delivery = notification_delivery

    def list_my_notifications(
        self,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> DesktopApiResult[tuple[NotificationDto, ...]]:
        def read_notifications() -> tuple[NotificationDto, ...]:
            self._notification_delivery.drain_pending()
            return tuple(
                self._notification_queries.list_my_notifications(
                    unread_only=unread_only,
                    limit=limit,
                )
            )

        return execute_desktop_operation(read_notifications)

    def count_my_unread(self) -> DesktopApiResult[int]:
        def count_notifications() -> int:
            self._notification_delivery.drain_pending()
            return self._notification_queries.count_my_unread()

        return execute_desktop_operation(count_notifications)

    def mark_read(self, notification_id: str) -> DesktopApiResult[NotificationDto]:
        return execute_desktop_operation(
            lambda: self._notification_commands.mark_read(notification_id)
        )

    def mark_all_read(self) -> DesktopApiResult[int]:
        return execute_desktop_operation(self._notification_commands.mark_all_read)

__all__ = ["PlatformNotificationDesktopApi"]
