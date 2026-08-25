from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from src.core.shared.events.domain_events import domain_events
from src.ui_qml.platform.presenters import (
    PlatformControlQueuePresenter,
    PlatformControlWorkspacePresenter,
)

from ..common import (
    WORKSPACE_PERMISSIONS,
    PlatformWorkspaceControllerBase,
    serialize_action_item,
    serialize_action_list,
    serialize_operation_result,
    serialize_workspace_overview,
)

QML_IMPORT_NAME = "Platform.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Platform workspace controllers are provided by the shell runtime.")
class PlatformControlWorkspaceController(PlatformWorkspaceControllerBase):
    approvalQueueChanged = Signal()
    auditFeedChanged = Signal()
    approvalStatusFilterChanged = Signal()
    approvalEntityTypeFilterChanged = Signal()
    auditEntityTypeFilterChanged = Signal()
    auditOperationFilterChanged = Signal()
    auditSeverityFilterChanged = Signal()

    def __init__(
        self,
        *,
        overview_presenter: PlatformControlWorkspacePresenter,
        queue_presenter: PlatformControlQueuePresenter,
        runtime_api=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._queue_presenter = queue_presenter
        self._runtime_api = runtime_api
        self._loaded = False
        self._approval_queue_table_model = DynamicTableModel(self)
        self._audit_feed_table_model = DynamicTableModel(self)
        self._approval_queue: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._audit_feed: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._approval_status_filter = ""
        self._approval_entity_type_filter = ""
        self._audit_entity_type_filter = ""
        self._audit_operation_filter = ""
        self._audit_severity_filter = ""
        self._bind_domain_events()

    @Property(str, notify=approvalStatusFilterChanged)
    def approvalStatusFilter(self) -> str:
        return self._approval_status_filter

    @Slot(str)
    def setApprovalStatusFilter(self, value: str) -> None:
        normalized = value or ""
        if normalized == self._approval_status_filter:
            return
        self._approval_status_filter = normalized
        self.approvalStatusFilterChanged.emit()
        self.refresh()

    @Property(str, notify=approvalEntityTypeFilterChanged)
    def approvalEntityTypeFilter(self) -> str:
        return self._approval_entity_type_filter

    @Slot(str)
    def setApprovalEntityTypeFilter(self, value: str) -> None:
        normalized = value or ""
        if normalized == self._approval_entity_type_filter:
            return
        self._approval_entity_type_filter = normalized
        self.approvalEntityTypeFilterChanged.emit()
        self.refresh()

    @Property(str, notify=auditEntityTypeFilterChanged)
    def auditEntityTypeFilter(self) -> str:
        return self._audit_entity_type_filter

    @Slot(str)
    def setAuditEntityTypeFilter(self, value: str) -> None:
        normalized = value or ""
        if normalized == self._audit_entity_type_filter:
            return
        self._audit_entity_type_filter = normalized
        self.auditEntityTypeFilterChanged.emit()
        self.refresh()

    @Property(str, notify=auditOperationFilterChanged)
    def auditOperationFilter(self) -> str:
        return self._audit_operation_filter

    @Slot(str)
    def setAuditOperationFilter(self, value: str) -> None:
        normalized = value or ""
        if normalized == self._audit_operation_filter:
            return
        self._audit_operation_filter = normalized
        self.auditOperationFilterChanged.emit()
        self.refresh()

    @Property(str, notify=auditSeverityFilterChanged)
    def auditSeverityFilter(self) -> str:
        return self._audit_severity_filter

    @Slot(str)
    def setAuditSeverityFilter(self, value: str) -> None:
        normalized = value or ""
        if normalized == self._audit_severity_filter:
            return
        self._audit_severity_filter = normalized
        self.auditSeverityFilterChanged.emit()
        self.refresh()

    @Property("QVariantMap", notify=approvalQueueChanged)
    def approvalQueue(self) -> dict[str, object]:
        return self._approval_queue

    @Property("QVariantMap", notify=auditFeedChanged)
    def auditFeed(self) -> dict[str, object]:
        return self._audit_feed

    @Property(QObject, constant=True)
    def approvalQueueTableModel(self) -> DynamicTableModel:
        return self._approval_queue_table_model

    @Property(QObject, constant=True)
    def auditFeedTableModel(self) -> DynamicTableModel:
        return self._audit_feed_table_model

    @Slot()
    def refresh(self) -> None:
        self._loaded = True
        self._set_is_loading(True)
        self._set_error_message("")
        self._set_overview(serialize_workspace_overview(self._overview_presenter.build_overview()))
        self._set_approval_queue(serialize_action_list(self._queue_presenter.build_approval_queue(
            status=self._approval_status_filter or None,
            entity_type=self._approval_entity_type_filter or None,
        )))
        self._set_audit_feed(serialize_action_list(self._queue_presenter.build_audit_feed(
            entity_type=self._audit_entity_type_filter or None,
            operation=self._audit_operation_filter or None,
            severity=self._audit_severity_filter or None,
        )))
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

    def _is_accessible(self) -> bool:
        return self._has_permission(WORKSPACE_PERMISSIONS["control"])

    def _bind_domain_events(self) -> None:
        # P5B-3: `modules_changed` removed here (not migrated) -- traced end-to-end, this
        # workspace's `refresh()` never reads any module-entitlement state (only the approval
        # queue and audit feed); the subscription was incidental over-refresh from the coarse
        # legacy signal, not a genuine dependency (see the P5B-3 report's consumer-chain trace).
        for signal in (
            domain_events.approvals_changed,
            domain_events.project_changed,
            domain_events.tasks_changed,
            domain_events.costs_changed,
            domain_events.resources_changed,
            domain_events.baseline_changed,
            domain_events.register_changed,
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
        self._approval_queue_table_model.set_rows(approval_queue.get("items", []))
        self.approvalQueueChanged.emit()

    def _set_audit_feed(self, audit_feed: dict[str, object]) -> None:
        if audit_feed == self._audit_feed:
            return
        self._audit_feed = audit_feed
        self._audit_feed_table_model.set_rows(audit_feed.get("items", []))
        self.auditFeedChanged.emit()


__all__ = ["PlatformControlWorkspaceController"]
