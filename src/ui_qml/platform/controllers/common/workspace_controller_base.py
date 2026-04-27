from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot


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

    def _set_is_busy(self, value: bool) -> None:
        if value == self._is_busy:
            return
        self._is_busy = value
        self.isBusyChanged.emit()

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


__all__ = [
    "PlatformWorkspaceControllerBase",
]