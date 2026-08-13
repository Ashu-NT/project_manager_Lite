from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.core.platform.domain.events.notifications import Notification


class NotificationRepository(ABC):
    @abstractmethod
    def add(self, notification: Notification) -> None: ...

    @abstractmethod
    def get(self, notification_id: str) -> Notification | None: ...

    @abstractmethod
    def list_for_user(
        self,
        user_id: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]: ...

    @abstractmethod
    def mark_read(self, notification_id: str, *, read_at: datetime) -> None: ...


__all__ = ["NotificationRepository"]
