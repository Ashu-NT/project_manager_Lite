from __future__ import annotations

from typing import Protocol

from src.core.platform.domain.events.notifications import Notification


class NotificationChannel(Protocol):
    """One external delivery channel (email, SMS, webhook, ...).

    No implementations exist yet. `NotificationService` always persists the
    in-app notification regardless of registered channels; channels are a
    zero-or-more fan-out on top of that, so adding a real one later never
    requires changing any caller of `NotificationService.dispatch`.
    """

    def send(self, notification: Notification) -> None: ...


__all__ = ["NotificationChannel"]
