from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.core.platform.domain.notifications import Notification


class NotificationRepository(ABC):
    @abstractmethod
    def add(self, notification: Notification) -> None: ...

    @abstractmethod
    def add_idempotent(self, notification: Notification) -> tuple[Notification, bool]: ...

    @abstractmethod
    def get_for_user(
        self, notification_id: str, *, user_id: str,
        tenant_id: str | None, organization_id: str | None,
    ) -> Notification | None: ...

    @abstractmethod
    def list_for_user(
        self,
        user_id: str,
        *,
        tenant_id: str | None,
        organization_id: str | None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]: ...

    @abstractmethod
    def mark_read(
        self, notification_id: str, *, user_id: str,
        tenant_id: str | None, organization_id: str | None, read_at: datetime,
    ) -> None: ...

    @abstractmethod
    def count_unread_for_user(
        self, user_id: str, *, tenant_id: str | None, organization_id: str | None,
    ) -> int: ...

    @abstractmethod
    def mark_all_read_for_user(
        self, user_id: str, *, tenant_id: str | None,
        organization_id: str | None, read_at: datetime,
    ) -> int: ...


__all__ = ["NotificationRepository"]
