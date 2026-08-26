from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.shared.events.signal import Signal as DomainSignal

QML_IMPORT_NAME = "Platform.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
@QmlUncreatable("Platform workspace controllers are provided by the shell runtime.")
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
        self._loaded = True
        self._domain_event_subscriptions: list[
            tuple[DomainSignal[Any], Callable[[Any], None]]
        ] = []
        self.destroyed.connect(self._disconnect_domain_event_subscriptions)

    def _diagnostic_context(self) -> dict[str, object]:
        return {
            "controller": type(self).__name__,
            "title": str(self._overview.get("title", "") or ""),
        }

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

    @Slot()
    def ensureLoaded(self) -> None:
        """Call when this workspace becomes active for the first time.
        No-ops if already loaded (including for every controller that
        hasn't opted into lazy loading, which stays permanently
        "already loaded"), or if the current session can't access this
        workspace anyway (_is_accessible() -- a perf pre-filter only, the
        backend still enforces this independently regardless)."""
        if self._loaded:
            return
        if not self._is_accessible():
            return
        refresh = getattr(self, "refresh", None)
        if callable(refresh):
            refresh()

    def _is_accessible(self) -> bool:
        """Override in a subclass that opts into lazy loading to report
        whether the current session can access this workspace at all.
        Default True: attempt the load regardless (matches every
        controller that hasn't opted in, and fails open when permission
        data can't be determined)."""
        return True

    def _has_permission(self, codes: tuple[str, ...]) -> bool:
        """Fail-open permission check shared by _is_accessible()
        overrides: True if the current session holds any of `codes`, or
        if permission data is unavailable (no runtime API wired, or a
        transient error) -- this is a client-side optimization only, never
        the actual authorization boundary, which the backend enforces
        independently on every call regardless of this result."""
        runtime_api = getattr(self, "_runtime_api", None)
        if runtime_api is None:
            return True
        result = runtime_api.get_current_permissions()
        if not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return True
        permissions = frozenset(result.data)
        return any(code in permissions for code in codes)

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
        if value:
            logger.error("Platform controller error message set context=%s message=%s", self._diagnostic_context(), value)
        else:
            logger.debug("Platform controller error message cleared context=%s", self._diagnostic_context())

    def _set_feedback_message(self, value: str) -> None:
        if value == self._feedback_message:
            return
        self._feedback_message = value
        self.feedbackMessageChanged.emit()
        if value:
            logger.info("Platform controller feedback message set context=%s message=%s", self._diagnostic_context(), value)
        else:
            logger.debug("Platform controller feedback message cleared context=%s", self._diagnostic_context())

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
        logger.debug(
            "Platform domain signal subscribed context=%s subscription_count=%s",
            self._diagnostic_context(),
            len(self._domain_event_subscriptions),
        )

    def _request_domain_refresh(self) -> None:
        if not self._loaded:
            # Never activated (lazy-loading controllers only -- always
            # True for everyone else) -- no background load; the eventual
            # first ensureLoaded() call fetches fresh data anyway, so
            # there is nothing stale to invalidate yet.
            return
        if self._is_loading or self._is_busy:
            self._pending_domain_refresh = True
            logger.debug(
                "Platform domain refresh queued context=%s is_loading=%s is_busy=%s",
                self._diagnostic_context(),
                self._is_loading,
                self._is_busy,
            )
            return
        refresh = getattr(self, "refresh", None)
        if callable(refresh):
            logger.debug("Platform domain refresh executing context=%s", self._diagnostic_context())
            refresh()

    def _flush_pending_domain_refresh(self) -> None:
        if not self._pending_domain_refresh or self._is_loading or self._is_busy:
            return
        self._pending_domain_refresh = False
        refresh = getattr(self, "refresh", None)
        if callable(refresh):
            logger.debug("Platform pending domain refresh executing context=%s", self._diagnostic_context())
            refresh()

    def _disconnect_domain_event_subscriptions(
        self,
        _object: QObject | None = None,
    ) -> None:
        for signal, callback in self._domain_event_subscriptions:
            try:
                signal.disconnect(callback)
            except Exception:
                logger.debug("Platform domain signal disconnect failed context=%s", self._diagnostic_context(), exc_info=True)
        self._domain_event_subscriptions.clear()
        logger.debug("Platform domain signal subscriptions cleared context=%s", self._diagnostic_context())


__all__ = [
    "PlatformWorkspaceControllerBase",
]
