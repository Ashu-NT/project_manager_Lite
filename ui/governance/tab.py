from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.exceptions import BusinessRuleError, NotFoundError
from core.models import ApprovalRequest, ApprovalStatus
from core.services.approval import ApprovalService
from core.services.project import ProjectService
from ui.settings import MainWindowSettingsStore
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class GovernanceTab(QWidget):
    def __init__(
        self,
        approval_service: ApprovalService,
        project_service: ProjectService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._approval_service = approval_service
        self._project_service = project_service
        self._settings_store = MainWindowSettingsStore()
        self._rows: list[ApprovalRequest] = []
        self._setup_ui()
        self.reload_requests()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Governance Queue")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel("Review, approve, or reject controlled baseline, dependency, and cost changes.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        mode_default = os.getenv("PM_GOVERNANCE_MODE", "off")
        self._governance_mode = self._settings_store.load_governance_mode(
            default_mode=mode_default
        )
        os.environ["PM_GOVERNANCE_MODE"] = self._governance_mode

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Governance:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Off", userData="off")
        self.mode_combo.addItem("On (Approval Required)", userData="required")
        mode_idx = self.mode_combo.findData(self._governance_mode)
        self.mode_combo.setCurrentIndex(mode_idx if mode_idx >= 0 else 0)
        self.mode_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        toolbar.addWidget(self.mode_combo)
        toolbar.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("Pending", userData=ApprovalStatus.PENDING)
        self.status_combo.addItem("All", userData=None)
        self.status_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_approve = QPushButton("Approve & Apply")
        self.btn_reject = QPushButton("Reject")
        for btn in (self.btn_refresh, self.btn_approve, self.btn_reject):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        toolbar.addWidget(self.status_combo)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_approve)
        toolbar.addWidget(self.btn_reject)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Requested At", "Status", "Type", "Entity", "Project", "Requested By", "Decision"]
        )
        style_table(self.table)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        self.status_combo.currentIndexChanged.connect(self.reload_requests)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.btn_refresh.clicked.connect(self.reload_requests)
        self.btn_approve.clicked.connect(self.approve_selected)
        self.btn_reject.clicked.connect(self.reject_selected)
        self.table.itemSelectionChanged.connect(self._sync_buttons)
        self._sync_buttons()

    def reload_requests(self) -> None:
        selected = self.status_combo.currentData()
        if selected is None:
            self._rows = self._approval_service.list_recent(limit=500)
        else:
            self._rows = self._approval_service.list_pending(limit=500)
        project_name_by_id = {p.id: p.name for p in self._project_service.list_projects()}

        self.table.setRowCount(len(self._rows))
        for row, request in enumerate(self._rows):
            project_label = project_name_by_id.get(request.project_id or "", request.project_id or "-")
            values = (
                request.requested_at.strftime("%Y-%m-%d %H:%M"),
                request.status.value,
                request.request_type,
                f"{request.entity_type}:{request.entity_id}",
                project_label,
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
        self._sync_buttons()

    def _selected_request_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def approve_selected(self) -> None:
        request_id = self._selected_request_id()
        if not request_id:
            return
        note, ok = QInputDialog.getText(
            self,
            "Approve Request",
            "Approval note (optional):",
        )
        if not ok:
            return
        try:
            self._approval_service.approve_and_apply(request_id, note=note or None)
        except (BusinessRuleError, NotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "Governance", str(exc))
            return
        self.reload_requests()

    def reject_selected(self) -> None:
        request_id = self._selected_request_id()
        if not request_id:
            return
        note, ok = QInputDialog.getText(
            self,
            "Reject Request",
            "Rejection reason (optional):",
        )
        if not ok:
            return
        try:
            self._approval_service.reject(request_id, note=note or None)
        except (BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Governance", str(exc))
            return
        self.reload_requests()

    def _sync_buttons(self) -> None:
        request_id = self._selected_request_id()
        can_decide = request_id is not None
        self.btn_approve.setEnabled(can_decide)
        self.btn_reject.setEnabled(can_decide)

    def _on_mode_changed(self, _index: int) -> None:
        mode = str(self.mode_combo.currentData() or "off").strip().lower()
        if mode not in {"off", "required"}:
            mode = "off"
        self._governance_mode = mode
        os.environ["PM_GOVERNANCE_MODE"] = mode
        self._settings_store.save_governance_mode(mode)
        QMessageBox.information(
            self,
            "Governance",
            (
                "Governance mode is now ON.\n"
                "Governed actions will create approval requests."
                if mode == "required"
                else "Governance mode is now OFF.\nGoverned actions apply immediately."
            ),
        )


__all__ = ["GovernanceTab"]
