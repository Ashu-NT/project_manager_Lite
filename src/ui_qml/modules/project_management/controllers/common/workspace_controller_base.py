from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.shared.events.signal import Signal as DomainSignal
from src.infra.platform.app_settings import AppSettingsStore

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementWorkspaceControllerBase(QObject):
    workspaceChanged = Signal()
    isLoadingChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    feedbackMessageChanged = Signal()
    emptyStateChanged = Signal()
    sectionErrorsChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_settings = AppSettingsStore()
        self._workspace: dict[str, object] = {
            "routeId": "",
            "title": "",
            "summary": "",
            "migrationStatus": "",
            "legacyRuntimeStatus": "",
        }
        self._is_loading = False
        self._is_busy = False
        self._error_message = ""
        self._feedback_message = ""
        self._empty_state = ""
        self._section_errors: dict[str, str] = {}
        self._pending_domain_refresh = False
        self._domain_refresh_scheduled = False
        self._domain_refresh_timer = QTimer(self)
        self._domain_refresh_timer.setSingleShot(True)
        self._domain_refresh_timer.timeout.connect(
            self._execute_scheduled_domain_refresh
        )
        self._domain_event_subscriptions: list[
            tuple[DomainSignal[Any], Callable[[Any], None]]
        ] = []
        self.destroyed.connect(self._disconnect_domain_event_subscriptions)

    @Property("QVariantMap", notify=workspaceChanged)
    def workspace(self) -> dict[str, object]:
        return self._workspace

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(bool, notify=isBusyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(str, notify=feedbackMessageChanged)
    def feedbackMessage(self) -> str:
        return self._feedback_message

    @Property(str, notify=emptyStateChanged)
    def emptyState(self) -> str:
        return self._empty_state

    @Property("QVariantMap", notify=sectionErrorsChanged)
    def sectionErrors(self) -> dict[str, str]:
        return self._section_errors

    @Slot()
    def clearMessages(self) -> None:
        self._set_error_message("")
        self._set_feedback_message("")

    @Slot(str, result="QVariantMap")
    def loadTableColumnState(self, table_id: str) -> dict[str, object]:
        return self._app_settings.load_table_column_state(table_id)

    @Slot(str, "QVariantMap")
    def saveTableColumnState(self, table_id: str, state: "dict[str, object]") -> None:
        self._app_settings.save_table_column_state(table_id, state)

    def _set_workspace(self, workspace: dict[str, object]) -> None:
        if workspace == self._workspace:
            return
        self._workspace = workspace
        self.workspaceChanged.emit()

    def _set_is_loading(self, value: bool) -> None:
        if value == self._is_loading:
            return
        self._is_loading = value
        self.isLoadingChanged.emit()
        if not value:
            self._flush_pending_domain_refresh()

    def _set_is_busy(self, value: bool) -> None:
        if value == self._is_busy:
            return
        self._is_busy = value
        self.isBusyChanged.emit()
        if not value:
            self._flush_pending_domain_refresh()

    def _set_error_message(self, value: str) -> None:
        if value == self._error_message:
            return
        self._error_message = value
        self.errorMessageChanged.emit()

    def _set_feedback_message(self, value: str) -> None:
        if value == self._feedback_message:
            return
        self._feedback_message = value
        self.feedbackMessageChanged.emit()

    def _set_empty_state(self, value: str) -> None:
        if value == self._empty_state:
            return
        self._empty_state = value
        self.emptyStateChanged.emit()

    def _set_section_error(self, section: str, error: str) -> None:
        new = {**self._section_errors, section: error}
        if new == self._section_errors:
            return
        self._section_errors = new
        self.sectionErrorsChanged.emit()

    def _clear_section_error(self, section: str) -> None:
        if self._section_errors.get(section, "") == "":
            return
        self._section_errors = {**self._section_errors, section: ""}
        self.sectionErrorsChanged.emit()

    def _subscribe_domain_signal(
        self,
        signal: DomainSignal[Any],
        callback: Callable[[Any], None],
    ) -> None:
        signal.connect(callback)
        self._domain_event_subscriptions.append((signal, callback))

    def _subscribe_domain_change(
        self,
        *entity_types: str,
        scope_code: str | None = None,
        category: str | None = None,
    ) -> None:
        allowed_entity_types = {
            entity_type.strip()
            for entity_type in entity_types
            if entity_type.strip()
        }

        def _handler(event: DomainChangeEvent) -> None:
            if category is not None and event.category != category:
                return
            if scope_code is not None and event.scope_code != scope_code:
                return
            if allowed_entity_types and event.entity_type not in allowed_entity_types:
                return
            self._request_domain_refresh()

        self._subscribe_domain_signal(domain_events.domain_changed, _handler)

    def _request_domain_refresh(self) -> None:
        self._pending_domain_refresh = True
        if self._is_loading or self._is_busy:
            return
        self._schedule_domain_refresh()

    def _flush_pending_domain_refresh(self) -> None:
        if not self._pending_domain_refresh or self._is_loading or self._is_busy:
            return
        self._schedule_domain_refresh()

    def _schedule_domain_refresh(self) -> None:
        if self._domain_refresh_scheduled:
            return
        self._domain_refresh_scheduled = True
        self._domain_refresh_timer.start(0)

    def _execute_scheduled_domain_refresh(self) -> None:
        self._domain_refresh_scheduled = False
        if self._is_loading or self._is_busy or not self._pending_domain_refresh:
            return
        self._pending_domain_refresh = False
        refresh = getattr(self, "refresh", None)
        if callable(refresh):
            refresh()

    def _disconnect_domain_event_subscriptions(
        self,
        _object: QObject | None = None,
    ) -> None:
        for signal, callback in self._domain_event_subscriptions:
            signal.disconnect(callback)
        self._domain_event_subscriptions.clear()


__all__ = ["ProjectManagementWorkspaceControllerBase"]
