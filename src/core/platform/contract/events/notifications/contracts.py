from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol

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


class NotificationChannel(Protocol):
    """One external delivery channel (email, SMS, webhook, ...).

    No implementations exist yet. `NotificationService` always persists the
    in-app notification regardless of registered channels; channels are a
    zero-or-more fan-out on top of that, so adding a real one later never
    requires changing any caller of `NotificationService.dispatch`.
    """

    def send(self, notification: Notification) -> None: ...


__all__ = ["NotificationChannel", "NotificationRepository"]
