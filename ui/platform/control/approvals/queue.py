from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.platform.approval import ApprovalService
from core.platform.approval.domain import ApprovalRequest, ApprovalStatus
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, NotFoundError
from core.platform.notifications.domain_events import domain_events
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.control.approvals.presentation import (
    approval_context_label,
    approval_display_label,
    approval_module_label,
)
from ui.platform.shared.guards import apply_permission_hint, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


SummaryChangedCallback = Callable[[int, str], None]


class ApprovalQueuePanel(QWidget):
    def __init__(
        self,
        *,
        approval_service: ApprovalService,
        user_session: UserSessionContext | None = None,
        summary_changed: SummaryChangedCallback | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._approval_service = approval_service
        self._user_session = user_session
        self._summary_changed = summary_changed
        self._rows: list[ApprovalRequest] = []
        self._can_view_approvals = bool(
            user_session is not None
            and (
                user_session.has_permission("approval.request")
                or user_session.has_permission("approval.decide")
            )
        )
        self._can_decide = bool(user_session is not None and user_session.has_permission("approval.decide"))
        self._setup_ui()
        self.reload_requests()
        domain_events.approvals_changed.connect(self._on_approvals_changed)

    @property
    def request_count(self) -> int:
        return len(self._rows)

    def current_status_label(self) -> str:
        return self.status_combo.currentText() or "Pending"

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(CFG.SPACING_MD)

        controls, controls_layout = build_admin_surface_card(
            object_name="approvalQueueControlSurface",
            alt=True,
        )
        toolbar = QHBoxLayout()
        self.status_combo = QComboBox()
        self.status_combo.addItem("Pending", userData=ApprovalStatus.PENDING)
        self.status_combo.addItem("Approved", userData=ApprovalStatus.APPROVED)
        self.status_combo.addItem("Rejected", userData=ApprovalStatus.REJECTED)
        self.status_combo.addItem("All", userData=None)
        self.status_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.status_combo.setEnabled(self._can_view_approvals)
        if not self._can_view_approvals:
            self.status_combo.setToolTip("Requires approval.request or approval.decide permission.")
        toolbar.addWidget(self.status_combo)
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_approve = QPushButton("Approve & Apply")
        self.btn_reject = QPushButton("Reject")
        for button in (self.btn_refresh, self.btn_approve, self.btn_reject):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_approve.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_reject.setStyleSheet(dashboard_action_button_style("danger"))
        toolbar.addWidget(self.btn_refresh)
        toolbar.addStretch(1)
        toolbar.addWidget(self.btn_approve)
        toolbar.addWidget(self.btn_reject)
        controls_layout.addLayout(toolbar)
        root.addWidget(controls)

        self.table = build_admin_table(
            headers=("Requested At", "Status", "Module", "Change Summary", "Context", "Requested By", "Decision"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
                QHeaderView.Stretch,
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
            ),
        )
        self.table.setEnabled(self._can_view_approvals)
        root.addWidget(self.table, 1)

        self.status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Approvals", callback=self.reload_requests)
        )
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Approvals", callback=self.reload_requests))
        self.btn_approve.clicked.connect(make_guarded_slot(self, title="Approvals", callback=self.approve_selected))
        self.btn_reject.clicked.connect(make_guarded_slot(self, title="Approvals", callback=self.reject_selected))
        self.table.itemSelectionChanged.connect(self._sync_buttons)
        apply_permission_hint(self.btn_approve, allowed=self._can_decide, missing_permission="approval.decide")
        apply_permission_hint(self.btn_reject, allowed=self._can_decide, missing_permission="approval.decide")
        self._sync_buttons()

    def reload_requests(self) -> None:
        if not self._can_view_approvals:
            self._rows = []
            self.table.setRowCount(0)
            self._emit_summary()
            self._sync_buttons()
            return
        selected = self.status_combo.currentData()
        try:
            self._rows = self._approval_service.list_requests(status=selected, limit=500)
        except (BusinessRuleError, NotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "Approvals", str(exc))
            self._rows = []
            self.table.setRowCount(0)
            self._emit_summary()
            self._sync_buttons()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Approvals", f"Failed to load requests:\n{exc}")
            self._rows = []
            self.table.setRowCount(0)
            self._emit_summary()
            self._sync_buttons()
            return

        self.table.setRowCount(len(self._rows))
        for row, request in enumerate(self._rows):
            values = (
                request.requested_at.strftime("%Y-%m-%d %H:%M"),
                request.status.value,
                approval_module_label(request),
                approval_display_label(request),
                approval_context_label(request),
                request.requested_by_username or "system",
                request.decision_note or "",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 1:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, request.id)
        self.table.clearSelection()
        self._emit_summary()
        self._sync_buttons()

    def approve_selected(self) -> None:
        request_id = self._selected_request_id()
        if not request_id:
            return
        note, ok = QInputDialog.getText(self, "Approve Request", "Approval note (optional):")
        if not ok:
            return
        try:
            self._approval_service.approve_and_apply(request_id, note=note or None)
        except (BusinessRuleError, NotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "Approvals", str(exc))
            return
        self.reload_requests()

    def reject_selected(self) -> None:
        request_id = self._selected_request_id()
        if not request_id:
            return
        note, ok = QInputDialog.getText(self, "Reject Request", "Rejection reason (optional):")
        if not ok:
            return
        try:
            self._approval_service.reject(request_id, note=note or None)
        except (BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Approvals", str(exc))
            return
        self.reload_requests()

    def _selected_request_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _sync_buttons(self) -> None:
        request_id = self._selected_request_id()
        can_decide = self._can_decide and request_id is not None
        self.btn_approve.setEnabled(can_decide)
        self.btn_reject.setEnabled(can_decide)
        if not self._can_decide:
            self.btn_approve.setToolTip("Requires approval.decide permission.")
            self.btn_reject.setToolTip("Requires approval.decide permission.")

    def _emit_summary(self) -> None:
        if self._summary_changed is not None:
            self._summary_changed(len(self._rows), self.current_status_label())

    def _on_approvals_changed(self, _request_id: str) -> None:
        self.reload_requests()


__all__ = ["ApprovalQueuePanel"]
