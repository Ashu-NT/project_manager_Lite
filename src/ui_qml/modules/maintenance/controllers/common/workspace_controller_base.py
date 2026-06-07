from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.shared.events.domain_events import (
    DomainChangeEvent,
    domain_events,
)
from src.core.shared.events.signal import Signal as DomainSignal

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenanceWorkspaceControllerBase(QObject):
    workspaceChanged = Signal()
    isLoadingChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    feedbackMessageChanged = Signal()
    emptyStateChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
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
        self._pending_domain_refresh = False
        self._domain_event_subscriptions: list[
            tuple[DomainSignal[Any], Callable[[Any], None]]
        ] = []
        self.destroyed.connect(self._disconnect_domain_event_subscriptions)

    def _diagnostic_context(self) -> dict[str, object]:
        return {
            "controller": type(self).__name__,
            "route_id": str(self._workspace.get("routeId", "") or ""),
            "title": str(self._workspace.get("title", "") or ""),
        }

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

    @Slot()
    def clearMessages(self) -> None:
        self._set_error_message("")
        self._set_feedback_message("")

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
        if value:
            logger.error("Maintenance controller error message set context=%s message=%s", self._diagnostic_context(), value)
        else:
            logger.debug("Maintenance controller error message cleared context=%s", self._diagnostic_context())

    def _set_feedback_message(self, value: str) -> None:
        if value == self._feedback_message:
            return
        self._feedback_message = value
        self.feedbackMessageChanged.emit()
        if value:
            logger.info("Maintenance controller feedback message set context=%s message=%s", self._diagnostic_context(), value)
        else:
            logger.debug("Maintenance controller feedback message cleared context=%s", self._diagnostic_context())

    def _set_empty_state(self, value: str) -> None:
        if value == self._empty_state:
            return
        self._empty_state = value
        self.emptyStateChanged.emit()

    def _subscribe_domain_signal(
        self,
        signal: DomainSignal[Any],
        callback: Callable[[Any], None],
    ) -> None:
        signal.connect(callback)
        self._domain_event_subscriptions.append((signal, callback))
        logger.debug(
            "Maintenance domain signal subscribed context=%s subscription_count=%s",
            self._diagnostic_context(),
            len(self._domain_event_subscriptions),
        )

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
            logger.debug(
                "Maintenance domain change matched context=%s entity_type=%s entity_id=%s scope=%s category=%s",
                self._diagnostic_context(),
                event.entity_type,
                event.entity_id,
                event.scope_code,
                event.category,
            )
            self._request_domain_refresh()

        self._subscribe_domain_signal(domain_events.domain_changed, _handler)
        logger.debug(
            "Maintenance domain change filter registered context=%s entity_types=%s scope=%s category=%s",
            self._diagnostic_context(),
            sorted(allowed_entity_types),
            scope_code or "-",
            category or "-",
        )

    def _request_domain_refresh(self) -> None:
        if self._is_loading or self._is_busy:
            self._pending_domain_refresh = True
            logger.debug(
                "Maintenance domain refresh queued context=%s is_loading=%s is_busy=%s",
                self._diagnostic_context(),
                self._is_loading,
                self._is_busy,
            )
            return
        refresh = getattr(self, "refresh", None)
        if callable(refresh):
            logger.info("Maintenance domain refresh executing context=%s", self._diagnostic_context())
            refresh()

    def _flush_pending_domain_refresh(self) -> None:
        if not self._pending_domain_refresh or self._is_loading or self._is_busy:
            return
        self._pending_domain_refresh = False
        refresh = getattr(self, "refresh", None)
        if callable(refresh):
            logger.info("Maintenance pending domain refresh executing context=%s", self._diagnostic_context())
            refresh()

    def _disconnect_domain_event_subscriptions(
        self,
        _object: QObject | None = None,
    ) -> None:
        for signal, callback in self._domain_event_subscriptions:
            try:
                signal.disconnect(callback)
            except Exception:
                logger.debug("Maintenance domain signal disconnect failed context=%s", self._diagnostic_context(), exc_info=True)
        self._domain_event_subscriptions.clear()
        logger.debug("Maintenance domain signal subscriptions cleared context=%s", self._diagnostic_context())


__all__ = ["MaintenanceWorkspaceControllerBase"]
