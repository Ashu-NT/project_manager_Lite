from __future__ import annotations

from typing import Protocol

from src.core.platform.domain.notifications import Notification


class NotificationQueries(Protocol):
    def list_my_notifications(self, *, unread_only: bool = False, limit: int = 50) -> list[Notification]: ...

    def count_my_unread(self) -> int: ...


class NotificationCommands(Protocol):
    def mark_read(self, notification_id: str) -> Notification: ...

    def mark_all_read(self) -> int: ...


class NotificationDeliveryRuntime(Protocol):
    def drain_pending(self) -> int: ...
