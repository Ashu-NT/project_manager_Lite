from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.core.platform.notifications.domain_events import domain_events
from src.ui_qml.platform.presenters import (
    PlatformControlQueuePresenter,
    PlatformControlWorkspacePresenter,
)

from ..common import (
    PlatformWorkspaceControllerBase,
    serialize_action_item,
    serialize_action_list,
    serialize_operation_result,
    serialize_workspace_overview,
)


class PlatformControlWorkspaceController(PlatformWorkspaceControllerBase):
    approvalQueueChanged = Signal()
    auditFeedChanged = Signal()

    def __init__(
        self,
        *,
        overview_presenter: PlatformControlWorkspacePresenter,
        queue_presenter: PlatformControlQueuePresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._queue_presenter = queue_presenter
        self._approval_queue: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._audit_feed: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=approvalQueueChanged)
    def approvalQueue(self) -> dict[str, object]:
        return self._approval_queue

    @Property("QVariantMap", notify=auditFeedChanged)
    def auditFeed(self) -> dict[str, object]:
        return self._audit_feed

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._set_overview(serialize_workspace_overview(self._overview_presenter.build_overview()))
        self._set_approval_queue(serialize_action_list(self._queue_presenter.build_approval_queue()))
        self._set_audit_feed(serialize_action_list(self._queue_presenter.build_audit_feed()))
        has_items = bool(self._approval_queue.get("items") or self._audit_feed.get("items"))
        self._set_empty_state("" if has_items else str(self._approval_queue.get("emptyState") or self._audit_feed.get("emptyState") or ""))
        self._set_is_loading(False)

    @Slot(str)
    def approveRequest(self, request_id: str) -> None:
        self.approveRequestWithNote(request_id, "")

    @Slot(str, str)
    def approveRequestWithNote(self, request_id: str, note: str) -> None:
        self._apply_request_action(
            request_id=request_id,
            note=note,
            operation=self._queue_presenter.approve_request,
            success_message="Approval request approved and applied.",
        )

    @Slot(str)
    def rejectRequest(self, request_id: str) -> None:
        self.rejectRequestWithNote(request_id, "")

    @Slot(str, str)
    def rejectRequestWithNote(self, request_id: str, note: str) -> None:
        self._apply_request_action(
            request_id=request_id,
            note=note,
            operation=self._queue_presenter.reject_request,
            success_message="Approval request rejected.",
        )

    def _bind_domain_events(self) -> None:
        for signal in (
            domain_events.approvals_changed,
            domain_events.project_changed,
            domain_events.tasks_changed,
            domain_events.costs_changed,
            domain_events.resources_changed,
            domain_events.baseline_changed,
            domain_events.register_changed,
            domain_events.modules_changed,
        ):
            self._subscribe_domain_signal(signal, self._on_domain_event)

    def _on_domain_event(self, _payload: object) -> None:
        self._request_domain_refresh()

    def _apply_request_action(
        self,
        *,
        request_id: str,
        note: str,
        operation,
        success_message: str,
    ) -> None:
        normalized_id = request_id.strip()
        if not normalized_id:
            return
        self._set_is_busy(True)
        self._set_error_message("")
        result = operation(normalized_id, note)
        payload = serialize_operation_result(result, success_message=success_message)
        self._set_operation_result(payload)
        if payload["ok"] and getattr(result, "data", None) is not None:
            self._set_feedback_message(str(payload["message"]))
            self._apply_request_update(result.data)
        else:
            self._set_feedback_message("")
            self._set_error_message(str(payload["message"]))
        self._set_is_busy(False)

    def _apply_request_update(self, request) -> None:
        items = [dict(item) for item in self._approval_queue.get("items", [])]
        updated = False
        serialized_item = serialize_action_item(self._queue_presenter.serialize_approval_item(request))
        for index, item in enumerate(items):
            if item.get("id") != request.id:
                continue
            items[index] = serialized_item
            updated = True
            break
        if not updated:
            self.refresh()
            return
        approval_queue = dict(self._approval_queue)
        approval_queue["items"] = items
        self._set_approval_queue(approval_queue)
        self._update_control_metrics()
        self._set_empty_state("" if items or self._audit_feed.get("items") else str(self._approval_queue.get("emptyState") or ""))

    def _update_control_metrics(self) -> None:
        items = self._approval_queue.get("items", [])
        pending_count = sum(1 for item in items if str((item.get("state") or {}).get("status", "")).lower() == "pending")
        approved_count = sum(1 for item in items if str((item.get("state") or {}).get("status", "")).lower() == "approved")
        rejected_count = sum(1 for item in items if str((item.get("state") or {}).get("status", "")).lower() == "rejected")
        metrics = [
            {
                "label": "Pending approvals",
                "value": str(pending_count),
                "supportingText": "Requests awaiting decision",
            },
            {
                "label": "Approved",
                "value": str(approved_count),
                "supportingText": "Requests already applied",
            },
            {
                "label": "Rejected",
                "value": str(rejected_count),
                "supportingText": "Requests closed without apply",
            },
            {
                "label": "Audit entries",
                "value": str(len(self._audit_feed.get("items", []))),
                "supportingText": "Recent governance and activity trail",
            },
        ]
        overview = dict(self._overview)
        overview["metrics"] = metrics
        self._set_overview(overview)

    def _set_approval_queue(self, approval_queue: dict[str, object]) -> None:
        if approval_queue == self._approval_queue:
            return
        self._approval_queue = approval_queue
        self.approvalQueueChanged.emit()

    def _set_audit_feed(self, audit_feed: dict[str, object]) -> None:
        if audit_feed == self._audit_feed:
            return
        self._audit_feed = audit_feed
        self.auditFeedChanged.emit()


__all__ = ["PlatformControlWorkspaceController"]
