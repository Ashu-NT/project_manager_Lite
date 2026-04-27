from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot


def serialize_workspace_overview(overview) -> dict[str, object]:
    return {
        "title": overview.title,
        "subtitle": overview.subtitle,
        "statusLabel": overview.status_label,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in overview.metrics
        ],
        "sections": [
            {
                "title": section.title,
                "emptyState": section.empty_state,
                "rows": [
                    {
                        "label": row.label,
                        "value": row.value,
                        "supportingText": row.supporting_text,
                    }
                    for row in section.rows
                ],
            }
            for section in overview.sections
        ],
    }


def serialize_action_list(list_view_model) -> dict[str, object]:
    return {
        "title": list_view_model.title,
        "subtitle": list_view_model.subtitle,
        "emptyState": list_view_model.empty_state,
        "items": [serialize_action_item(item) for item in list_view_model.items],
    }


def serialize_action_item(item) -> dict[str, object]:
    return {
        "id": item.id,
        "title": item.title,
        "statusLabel": item.status_label,
        "subtitle": item.subtitle,
        "supportingText": item.supporting_text,
        "metaText": item.meta_text,
        "canPrimaryAction": item.can_primary_action,
        "canSecondaryAction": item.can_secondary_action,
        "canTertiaryAction": item.can_tertiary_action,
        "state": dict(item.state),
    }


def serialize_operation_result(
    result,
    *,
    success_message: str,
) -> dict[str, object]:
    if result is not None and getattr(result, "ok", False):
        return {
            "ok": True,
            "category": "",
            "code": "",
            "message": success_message,
        }
    error = getattr(result, "error", None) if result is not None else None
    return {
        "ok": False,
        "category": getattr(error, "category", "domain"),
        "code": getattr(error, "code", "operation_failed"),
        "message": getattr(error, "message", "The platform QML action did not complete."),
    }


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
    "serialize_action_item",
    "serialize_action_list",
    "serialize_operation_result",
    "serialize_workspace_overview",
]