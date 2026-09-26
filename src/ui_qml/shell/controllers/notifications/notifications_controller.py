from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shell.presenters.notifications.notifications_presenter import (
    NotificationsPresenter,
)

QML_IMPORT_NAME = "Shell.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


def _serialize_row(vm) -> dict[str, object]:
    return {
        "id": vm.id,
        "title": vm.title,
        "body": vm.body,
        "category": vm.category,
        "timestampLabel": vm.timestamp_label,
        "isRead": vm.is_read,
    }


@QmlElement
@QmlUncreatable("Shell notifications controllers are provided by the application shell.")
class NotificationsController(QObject):
    """Shell-owned controller for the notification bell + drawer.

    Owns unread count, notification rows, loading/error state, and the
    mark-read/mark-all-read mutations. Subscribes to ShellContext.scopeChanged
    directly (mirrors GlobalOverviewController) so a tenant/organization
    switch clears stale badge/list state and reloads under the new scope --
    it does not know about GlobalOverviewController or any other controller.
    """

    unreadCountChanged = Signal()
    notificationsChanged = Signal()
    isLoadingChanged = Signal()
    errorMessageChanged = Signal()

    def __init__(
        self,
        *,
        presenter: NotificationsPresenter,
        shell_context=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._shell_context = shell_context
        self._unread_count = 0
        self._notifications: list[dict[str, object]] = []
        self._is_loading = False
        self._error_message = ""
        if shell_context is not None:
            shell_context.scopeChanged.connect(self._on_scope_changed)

    # -- properties ----------------------------------------------------------

    @Property(int, notify=unreadCountChanged)
    def unreadCount(self) -> int:
        return self._unread_count

    @Property("QVariantList", notify=notificationsChanged)
    def notifications(self) -> list[dict[str, object]]:
        return self._notifications

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    # -- slots ----------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        count_result = self._presenter.load_unread_count()
        list_result = self._presenter.load_notifications()
        self._set_is_loading(False)

        # Independent-ish, but both are read from the same underlying store
        # in one refresh -- either failing sets the shared error state; a
        # count success alongside a list failure still shows the exact badge.
        if count_result.ok:
            self._set_unread_count(int(count_result.data or 0))
        if list_result.ok:
            self._set_notifications([_serialize_row(vm) for vm in (list_result.data or ())])

        if not count_result.ok or not list_result.ok:
            message = (
                count_result.error_message
                if not count_result.ok
                else list_result.error_message
            )
            self._set_error_message(message or "")

    @Slot(str, result=bool)
    def markRead(self, notification_id: str) -> bool:
        normalized = str(notification_id or "").strip()
        if not normalized:
            return False
        result = self._presenter.mark_read(normalized)
        if not result.ok:
            self._set_error_message(result.error_message or "")
            return False
        self._set_error_message("")
        # Backend action already succeeded -- reload to get the authoritative
        # exact unread count and read state rather than guessing locally.
        self.refresh()
        return True

    @Slot(result=bool)
    def markAllRead(self) -> bool:
        result = self._presenter.mark_all_read()
        if not result.ok:
            self._set_error_message(result.error_message or "")
            return False
        self._set_error_message("")
        self.refresh()
        return True

    # -- scope change ----------------------------------------------------------

    def _on_scope_changed(self) -> None:
        self._set_unread_count(0)
        self._set_notifications([])
        self.refresh()

    # -- internal ----------------------------------------------------------

    def _set_unread_count(self, value: int) -> None:
        if value == self._unread_count:
            return
        self._unread_count = value
        self.unreadCountChanged.emit()

    def _set_notifications(self, value: list[dict[str, object]]) -> None:
        if value == self._notifications:
            return
        self._notifications = value
        self.notificationsChanged.emit()

    def _set_is_loading(self, value: bool) -> None:
        if value == self._is_loading:
            return
        self._is_loading = value
        self.isLoadingChanged.emit()

    def _set_error_message(self, value: str) -> None:
        if value == self._error_message:
            return
        self._error_message = value
        self.errorMessageChanged.emit()
        if value:
            logger.error("Notifications controller error message set message=%s", value)


__all__ = ["NotificationsController"]
