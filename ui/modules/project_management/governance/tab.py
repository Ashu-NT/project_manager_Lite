from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.platform.approval import ApprovalService
from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.time.application.timesheet_review import TimesheetReviewQueueItem
from core.modules.project_management.services.project import ProjectService
from core.modules.project_management.services.timesheet import TimesheetService
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.modules.project_management.governance.timesheet_review_dialog import TimesheetReviewDialog
from ui.modules.project_management.shared.domain_event_filters import is_project_management_domain_event
from src.ui.platform.workspaces.control.approvals.presentation import approval_display_label
from src.ui.platform.workspaces.control.approvals.queue import ApprovalQueuePanel
from src.ui.platform.settings import MainWindowSettingsStore
from src.ui.shared.widgets.guards import make_guarded_slot
from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class GovernanceTab(QWidget):
    def __init__(
        self,
        approval_service: ApprovalService,
        project_service: ProjectService,
        task_service: object | None = None,
        cost_service: object | None = None,
        timesheet_service: TimesheetService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._approval_service = approval_service
        self._project_service = project_service
        self._timesheet_service = timesheet_service
        self._user_session = user_session
        self._settings_store = MainWindowSettingsStore()
        self._timesheet_rows: list[TimesheetReviewQueueItem] = []
        self._project_name_by_id: dict[str, str] = {}
        self._can_view_approvals = bool(
            user_session is not None
            and (
                user_session.has_permission("approval.request")
                or user_session.has_permission("approval.decide")
            )
        )
        self._can_decide = bool(user_session is not None and user_session.has_permission("approval.decide"))
        self._can_review_timesheets = bool(
            timesheet_service is not None
            and user_session is not None
            and user_session.has_permission("timesheet.approve")
        )
        self._can_change_mode = bool(user_session is not None and user_session.has_permission("settings.manage"))
        self._setup_ui()
        self.reload_data()
        domain_events.domain_changed.connect(self._on_domain_change)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("governanceHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#governanceHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)
        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("GOVERNANCE")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.addWidget(eyebrow)
        title = QLabel("Governance")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.addWidget(title)
        subtitle = QLabel(
            "Manage PM governance mode, review project management governed changes, and process submitted timesheets."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.governance_mode_badge = QLabel("Off")
        self.governance_mode_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.governance_status_badge = QLabel("Pending")
        self.governance_status_badge.setStyleSheet(dashboard_meta_chip_style())
        self.governance_count_badge = QLabel("0 requests")
        self.governance_count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.governance_access_badge = QLabel(self._access_badge_label())
        self.governance_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.governance_mode_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.governance_status_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.governance_count_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.governance_access_badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        mode_default = os.getenv("PM_GOVERNANCE_MODE", "off")
        self._governance_mode = self._settings_store.load_governance_mode(default_mode=mode_default)
        os.environ["PM_GOVERNANCE_MODE"] = self._governance_mode

        self.queue_tabs = QTabWidget()
        self.queue_tabs.setDocumentMode(True)
        layout.addWidget(self.queue_tabs, 1)

        approvals_page = QWidget()
        approvals_layout = QVBoxLayout(approvals_page)
        approvals_layout.setContentsMargins(0, 0, 0, 0)
        approvals_layout.setSpacing(CFG.SPACING_MD)

        controls = QWidget()
        controls.setObjectName("governanceControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#governanceControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("PM Governance Mode"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Off", userData="off")
        self.mode_combo.addItem("On (Approval Required)", userData="required")
        mode_idx = self.mode_combo.findData(self._governance_mode)
        self.mode_combo.setCurrentIndex(mode_idx if mode_idx >= 0 else 0)
        self.mode_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.mode_combo.setEnabled(self._can_change_mode)
        if not self._can_change_mode:
            self.mode_combo.setToolTip("Requires settings.manage permission.")
        toolbar.addWidget(self.mode_combo)
        toolbar.addStretch(1)
        controls_layout.addLayout(toolbar)
        approvals_layout.addWidget(controls)

        self.approval_queue = ApprovalQueuePanel(
            approval_service=self._approval_service,
            user_session=self._user_session,
            summary_changed=self._update_header_badges,
            entity_type_filter=[
                "project_baseline",
                "task_dependency", 
                "cost_item",
                "resource",
            ],
            parent=self,
        )
        self.table = self.approval_queue.table
        self.status_combo = self.approval_queue.status_combo
        self.btn_refresh = self.approval_queue.btn_refresh
        self.btn_approve = self.approval_queue.btn_approve
        self.btn_reject = self.approval_queue.btn_reject
        approvals_layout.addWidget(self.approval_queue, 1)
        self.queue_tabs.addTab(approvals_page, "Governance Queue")

        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        if self._can_review_timesheets:
            timesheet_page = QWidget()
            timesheet_layout = QVBoxLayout(timesheet_page)
            timesheet_layout.setContentsMargins(0, 0, 0, 0)
            timesheet_layout.setSpacing(CFG.SPACING_MD)
            queue_label_row = QHBoxLayout()
            self.timesheet_queue_label = QLabel("Timesheet Review Queue")
            self.timesheet_queue_label.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
            self.timesheet_queue_badge = QLabel("0 pending periods")
            self.timesheet_queue_badge.setStyleSheet(dashboard_meta_chip_style())
            queue_label_row.addWidget(self.timesheet_queue_label)
            queue_label_row.addWidget(self.timesheet_queue_badge)
            queue_label_row.addStretch()
            self.btn_review_timesheet = QPushButton("Review Selected Period")
            self.btn_review_timesheet.setFixedHeight(CFG.BUTTON_HEIGHT)
            self.btn_review_timesheet.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            self.btn_review_timesheet.setStyleSheet(dashboard_action_button_style("primary"))
            queue_label_row.addWidget(self.btn_review_timesheet)
            timesheet_layout.addLayout(queue_label_row)

            queue_hint = QLabel(
                "Approvers work from this queue. Collaboration notifications are awareness-only; submitted periods are reviewed here."
            )
            queue_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
            queue_hint.setWordWrap(True)
            timesheet_layout.addWidget(queue_hint)

            self.timesheet_table = QTableWidget(0, 7)
            self.timesheet_table.setHorizontalHeaderLabels(
                ["Submitted", "Resource", "Period", "Hours", "Projects", "Submitted By", "Note"]
            )
            style_table(self.timesheet_table)
            timesheet_header = self.timesheet_table.horizontalHeader()
            timesheet_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            timesheet_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            timesheet_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            timesheet_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            timesheet_header.setSectionResizeMode(4, QHeaderView.Stretch)
            timesheet_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
            timesheet_header.setSectionResizeMode(6, QHeaderView.Stretch)
            timesheet_layout.addWidget(self.timesheet_table, 1)

            self.btn_review_timesheet.clicked.connect(
                make_guarded_slot(self, title="Timesheet Review", callback=self._review_selected_timesheet)
            )
            self.timesheet_table.itemSelectionChanged.connect(self._sync_timesheet_buttons)
            self.timesheet_table.itemDoubleClicked.connect(lambda _item: self._review_selected_timesheet())
            self._sync_timesheet_buttons()
            self.queue_tabs.addTab(timesheet_page, "Timesheet Review")
            if not self._can_view_approvals:
                self.queue_tabs.setCurrentWidget(timesheet_page)

    def reload_data(self) -> None:
        self.reload_requests()
        self._reload_timesheet_queue()

    def reload_requests(self) -> None:
        self.approval_queue.reload_requests()

    def _reload_timesheet_queue(self) -> None:
        if not self._can_review_timesheets or self._timesheet_service is None:
            return
        try:
            self._timesheet_rows = self._timesheet_service.list_timesheet_review_queue(limit=200)
            self._project_name_by_id = self._load_project_name_index()
        except (BusinessRuleError, NotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "Timesheet Review", str(exc))
            self._timesheet_rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Timesheet Review", f"Failed to load timesheet review queue:\n{exc}")
            self._timesheet_rows = []

        self.timesheet_table.setRowCount(len(self._timesheet_rows))
        for row_idx, item in enumerate(self._timesheet_rows):
            project_labels = ", ".join(
                self._project_name_by_id.get(project_id, project_id) for project_id in item.project_ids
            ) or "-"
            values = (
                item.submitted_at.strftime("%Y-%m-%d %H:%M") if item.submitted_at is not None else "-",
                item.resource_name,
                f"{item.period_start.isoformat()} to {item.period_end.isoformat()}",
                f"{item.total_hours:.2f}",
                project_labels,
                item.submitted_by_username or "system",
                item.decision_note or "",
            )
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if col == 0:
                    table_item.setData(Qt.UserRole, item.period_id)
                if col == 3:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.timesheet_table.setItem(row_idx, col, table_item)
        self.timesheet_table.clearSelection()
        self.timesheet_queue_badge.setText(f"{len(self._timesheet_rows)} pending periods")
        self._sync_timesheet_buttons()

    def _selected_timesheet_period_id(self) -> str | None:
        if not self._can_review_timesheets:
            return None
        row = self.timesheet_table.currentRow()
        if row < 0:
            return None
        item = self.timesheet_table.item(row, 0)
        return item.data(Qt.UserRole) if item is not None else None

    def _review_selected_timesheet(self) -> None:
        if not self._can_review_timesheets or self._timesheet_service is None:
            return
        period_id = self._selected_timesheet_period_id()
        if not period_id:
            QMessageBox.information(self, "Timesheet Review", "Select a submitted period first.")
            return
        summary = next((row for row in self._timesheet_rows if row.period_id == period_id), None)
        if summary is None:
            self._reload_timesheet_queue()
            return
        try:
            detail = self._timesheet_service.get_timesheet_review_detail(period_id)
        except (BusinessRuleError, NotFoundError, ValidationError) as exc:
            QMessageBox.warning(self, "Timesheet Review", str(exc))
            self._reload_timesheet_queue()
            return
        dialog = TimesheetReviewDialog(
            self,
            timesheet_service=self._timesheet_service,
            summary=summary,
            detail=detail,
            project_name_by_id=self._project_name_by_id,
            user_session=self._user_session,
        )
        dialog.exec()
        self._reload_timesheet_queue()

    def approve_selected(self) -> None:
        self.approval_queue.approve_selected()

    def reject_selected(self) -> None:
        self.approval_queue.reject_selected()

    def _sync_buttons(self) -> None:
        self.approval_queue._sync_buttons()

    def _sync_timesheet_buttons(self) -> None:
        if not self._can_review_timesheets:
            return
        self.btn_review_timesheet.setEnabled(self._selected_timesheet_period_id() is not None)

    def _on_mode_changed(self, _index: int) -> None:
        if not self._can_change_mode:
            return
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
        self._update_header_badges(self.approval_queue.request_count, self.approval_queue.current_status_label())

    def _on_domain_change(self, event) -> None:
        if event.category == "platform" and event.entity_type == "approval_request":
            self.reload_requests()
        elif is_project_management_domain_event(event, "timesheet_period"):
            self._reload_timesheet_queue()

    def _load_project_name_index(self) -> dict[str, str]:
        return {project.id: project.name for project in self._project_service.list_projects()}

    def _access_badge_label(self) -> str:
        if self._can_decide and self._can_review_timesheets:
            return "Approvals + Timesheets"
        if self._can_decide:
            return "Decision Enabled"
        if self._can_review_timesheets:
            return "Timesheet Review"
        if self._can_view_approvals:
            return "Request Tracking"
        return "Read Only"

    def _entity_display_label(
        self,
        *,
        request,
        project_name_by_id: dict[str, str],
        task_name_by_id: dict[str, str],
        cost_desc_by_id: dict[str, str],
    ) -> str:
        payload = request.payload or {}
        if request.request_type == "baseline.create" and not str(payload.get("project_name") or "").strip():
            baseline_name = str(payload.get("name") or "Baseline").strip() or "Baseline"
            project_name = project_name_by_id.get(request.project_id or "", "selected project")
            return f"Create baseline '{baseline_name}' for {project_name}"
        return approval_display_label(request)

    def _update_header_badges(self, visible_count: int, status_label: str | None = None) -> None:
        mode_label = "On" if self._governance_mode == "required" else "Off"
        badge_color = CFG.COLOR_ACCENT if self._governance_mode == "required" else CFG.COLOR_ACCENT_SOFT
        badge_foreground = "#FFFFFF" if self._governance_mode == "required" else CFG.COLOR_TEXT_PRIMARY
        self.governance_mode_badge.setText(mode_label)
        self.governance_mode_badge.setStyleSheet(dashboard_badge_style(badge_color, badge_foreground))
        status = status_label or self.status_combo.currentText() or "Pending"
        self.governance_status_badge.setText(status)
        self.governance_count_badge.setText(f"{visible_count} requests")


__all__ = ["GovernanceTab"]
