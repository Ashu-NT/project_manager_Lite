from __future__ import annotations

from datetime import datetime, timezone

from src.core.platform.api.desktop.events.notifications.models.notification import NotificationDto
from src.core.platform.api.desktop.models.common import DesktopApiError, DesktopApiResult
from src.ui_qml.shell.controllers.notifications.notifications_controller import (
    NotificationsController,
)
from src.ui_qml.shell.presenters.notifications.notifications_presenter import (
    NotificationsPresenter,
)


def _dto(id_: str, *, title: str = "Title", is_read: bool = False) -> NotificationDto:
    return NotificationDto(
        id=id_,
        category="test.event",
        title=title,
        body="Body",
        created_at=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        read_at=None if not is_read else datetime(2026, 9, 20, 11, 0, tzinfo=timezone.utc),
        is_read=is_read,
        metadata={},
    )


class _FakeNotificationApi:
    def __init__(self, *, notifications=(), unread_count: int = 0) -> None:
        self._notifications = list(notifications)
        self._unread_count = unread_count
        self.count_result: DesktopApiResult | None = None
        self.list_result: DesktopApiResult | None = None
        self.mark_read_result: DesktopApiResult | None = None
        self.mark_all_result: DesktopApiResult | None = None
        self.mark_read_calls: list[str] = []
        self.mark_all_calls = 0

    def count_my_unread(self):
        if self.count_result is not None:
            return self.count_result
        return DesktopApiResult(ok=True, data=self._unread_count)

    def list_my_notifications(self, *, unread_only: bool = False, limit: int = 50):
        if self.list_result is not None:
            return self.list_result
        return DesktopApiResult(ok=True, data=tuple(self._notifications))

    def mark_read(self, notification_id: str):
        self.mark_read_calls.append(notification_id)
        if self.mark_read_result is not None:
            return self.mark_read_result
        for i, n in enumerate(self._notifications):
            if n.id == notification_id:
                updated = _dto(n.id, title=n.title, is_read=True)
                self._notifications[i] = updated
                self._unread_count = max(0, self._unread_count - 1)
                return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(ok=False, error=DesktopApiError(code="X", message="not found", category="not_found"))

    def mark_all_read(self):
        self.mark_all_calls += 1
        if self.mark_all_result is not None:
            return self.mark_all_result
        updated_count = sum(1 for n in self._notifications if not n.is_read)
        self._notifications = [_dto(n.id, title=n.title, is_read=True) for n in self._notifications]
        self._unread_count = 0
        return DesktopApiResult(ok=True, data=updated_count)


def _controller(api, *, shell_context=None) -> NotificationsController:
    return NotificationsController(
        presenter=NotificationsPresenter(api=api), shell_context=shell_context
    )


# -- exact unread count -------------------------------------------------------------------


def test_unread_count_is_exact_not_capped_by_list_length():
    api = _FakeNotificationApi(
        notifications=[_dto("n1")], unread_count=55  # far more unread than the returned list
    )
    controller = _controller(api)

    controller.refresh()

    assert controller.unreadCount == 55


# -- list load -------------------------------------------------------------------


def test_notifications_list_loads_and_maps_rows():
    api = _FakeNotificationApi(notifications=[_dto("n1", title="Hello")], unread_count=1)
    controller = _controller(api)

    controller.refresh()

    assert len(controller.notifications) == 1
    assert controller.notifications[0]["title"] == "Hello"
    assert controller.notifications[0]["isRead"] is False


# -- empty -------------------------------------------------------------------


def test_empty_notifications_is_not_an_error():
    api = _FakeNotificationApi(notifications=[], unread_count=0)
    controller = _controller(api)

    controller.refresh()

    assert controller.notifications == []
    assert controller.unreadCount == 0
    assert controller.errorMessage == ""


# -- error -------------------------------------------------------------------


def test_list_failure_sets_friendly_error_message():
    api = _FakeNotificationApi()
    api.list_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )
    controller = _controller(api)

    controller.refresh()

    assert controller.errorMessage == "Notifications could not be loaded."
    assert "boom" not in controller.errorMessage


# -- mark read -------------------------------------------------------------------


def test_mark_read_decrements_unread_count_and_updates_row():
    api = _FakeNotificationApi(notifications=[_dto("n1")], unread_count=1)
    controller = _controller(api)
    controller.refresh()
    assert controller.unreadCount == 1

    ok = controller.markRead("n1")

    assert ok is True
    assert controller.unreadCount == 0
    assert controller.notifications[0]["isRead"] is True


def test_mark_read_failure_does_not_change_state_permanently():
    api = _FakeNotificationApi(notifications=[_dto("n1")], unread_count=1)
    api.mark_read_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )
    controller = _controller(api)
    controller.refresh()

    ok = controller.markRead("n1")

    assert ok is False
    assert controller.errorMessage != ""
    assert controller.unreadCount == 1


# -- mark all read -------------------------------------------------------------------


def test_mark_all_read_zeroes_unread_count_and_marks_all_rows_read():
    api = _FakeNotificationApi(
        notifications=[_dto("n1"), _dto("n2"), _dto("n3", is_read=True)], unread_count=2
    )
    controller = _controller(api)
    controller.refresh()

    ok = controller.markAllRead()

    assert ok is True
    assert controller.unreadCount == 0
    assert all(row["isRead"] for row in controller.notifications)


# -- scopeChanged reload -------------------------------------------------------------------


class _FakeShellContext:
    def __init__(self) -> None:
        self._handlers = []

        class _Signal:
            def __init__(self, outer):
                self._outer = outer

            def connect(self, handler):
                self._outer._handlers.append(handler)

            def emit(self):
                for handler in list(self._outer._handlers):
                    handler()

        self.scopeChanged = _Signal(self)


def test_scope_changed_reloads_and_clears_stale_data_first():
    api = _FakeNotificationApi(notifications=[_dto("n1")], unread_count=1)
    shell_context = _FakeShellContext()
    controller = _controller(api, shell_context=shell_context)
    controller.refresh()
    assert controller.unreadCount == 1

    # Simulate a new scope with completely different (initially empty) data,
    # and observe that stale old-scope values are cleared BEFORE the reload
    # actually re-populates them -- not left visible in between.
    observed_during_reload = []
    original_count = api.count_my_unread

    def _count_and_observe():
        observed_during_reload.append(controller.unreadCount)
        return original_count()

    api.count_my_unread = _count_and_observe
    api._notifications = [_dto("n2")]
    api._unread_count = 1

    shell_context.scopeChanged.emit()

    assert observed_during_reload == [0]
    assert controller.unreadCount == 1
    assert controller.notifications[0]["id"] == "n2"


def test_no_shell_context_does_not_crash_construction():
    api = _FakeNotificationApi()
    controller = _controller(api, shell_context=None)
    controller.refresh()
    assert controller.unreadCount == 0
