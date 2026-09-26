from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.api.desktop.events.notifications.models.notification import (
    NotificationDto,
)
from src.core.platform.api.desktop.events.notifications.notification import (
    PlatformNotificationDesktopApi,
)

_LOAD_ERROR = "Notifications could not be loaded."
_MARK_READ_ERROR = "Could not mark this notification as read."
_MARK_ALL_READ_ERROR = "Could not mark all notifications as read."


@dataclass(frozen=True)
class NotificationRowViewModel:
    id: str
    title: str
    body: str
    category: str
    timestamp_label: str
    is_read: bool


@dataclass(frozen=True)
class SectionResult:
    """Mirrors GlobalOverviewPresenter.SectionResult's shape -- ok/data or a
    business-friendly error message, never a raw exception/DesktopApiResult
    error leaking through."""

    ok: bool
    data: object | None
    error_message: str | None = None


class NotificationsPresenter:
    """Pure Python presentation mapping for the shell notifications drawer.

    NotificationDto carries no route/source information -- rows are
    therefore never presented as navigable here; see NotificationsController.
    """

    def __init__(self, *, api: PlatformNotificationDesktopApi | None = None) -> None:
        self._api = api

    def load_unread_count(self) -> SectionResult:
        if self._api is None:
            return SectionResult(ok=True, data=0)
        result = self._api.count_my_unread()
        if not result.ok or result.data is None:
            return SectionResult(ok=False, data=None, error_message=_LOAD_ERROR)
        return SectionResult(ok=True, data=int(result.data))

    def load_notifications(self, *, limit: int = 50) -> SectionResult:
        if self._api is None:
            return SectionResult(ok=True, data=())
        result = self._api.list_my_notifications(limit=limit)
        if not result.ok or result.data is None:
            return SectionResult(ok=False, data=None, error_message=_LOAD_ERROR)
        rows = tuple(self._build_row(dto) for dto in result.data)
        return SectionResult(ok=True, data=rows)

    def mark_read(self, notification_id: str) -> SectionResult:
        if self._api is None:
            return SectionResult(ok=False, data=None, error_message=_MARK_READ_ERROR)
        result = self._api.mark_read(notification_id)
        if not result.ok:
            return SectionResult(ok=False, data=None, error_message=_MARK_READ_ERROR)
        return SectionResult(ok=True, data=self._build_row(result.data) if result.data else None)

    def mark_all_read(self) -> SectionResult:
        if self._api is None:
            return SectionResult(ok=False, data=None, error_message=_MARK_ALL_READ_ERROR)
        result = self._api.mark_all_read()
        if not result.ok or result.data is None:
            return SectionResult(ok=False, data=None, error_message=_MARK_ALL_READ_ERROR)
        return SectionResult(ok=True, data=int(result.data))

    @staticmethod
    def _build_row(dto: NotificationDto) -> NotificationRowViewModel:
        return NotificationRowViewModel(
            id=dto.id,
            title=dto.title,
            body=dto.body,
            category=dto.category,
            timestamp_label=dto.created_at.strftime("%d %b %Y · %H:%M"),
            is_read=dto.is_read,
        )


__all__ = ["NotificationRowViewModel", "NotificationsPresenter", "SectionResult"]
