from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.notifications.signal import Signal as DomainSignal


class PlatformWorkspaceControllerBase(QObject):
    overviewChanged = Signal()
    isLoadingChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    feedbackMessageChanged = Signal()
    emptyStateChanged = Signal()
    operationResultChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "statusLabel": "", "metrics": [], "sections": []}
        self._is_loading = False
        self._is_busy = False
        self._error_message = ""
        self._feedback_message = ""
        self._empty_state = ""
        self._operation_result: dict[str, object] = {
            "ok": True,
            "category": "",
            "code": "",
            "message": "",
        }
        self._pending_domain_refresh = False
        self._domain_event_subscriptions: list[
            tuple[DomainSignal[Any], Callable[[Any], None]]
        ] = []
        self.destroyed.connect(self._disconnect_domain_event_subscriptions)

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

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

    @Property("QVariantMap", notify=operationResultChanged)
    def operationResult(self) -> dict[str, object]:
        return self._operation_result

    @Slot()
    def clearMessages(self) -> None:
        self._set_error_message("")
        self._set_feedback_message("")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

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

    def _set_operation_result(self, value: dict[str, object]) -> None:
        if value == self._operation_result:
            return
        self._operation_result = value
        self.operationResultChanged.emit()

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
        if self._is_loading or self._is_busy:
            self._pending_domain_refresh = True
            return
        refresh = getattr(self, "refresh", None)
        if callable(refresh):
            refresh()

    def _flush_pending_domain_refresh(self) -> None:
        if not self._pending_domain_refresh or self._is_loading or self._is_busy:
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


__all__ = [
    "PlatformWorkspaceControllerBase",
]
