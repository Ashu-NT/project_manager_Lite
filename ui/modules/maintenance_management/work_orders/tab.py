from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.platform import PlatformRuntimeApplicationService
from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenanceDocumentService,
    MaintenanceLocationService,
    MaintenanceSystemService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderService,
    MaintenanceWorkOrderTaskService,
    MaintenanceWorkOrderTaskStepService,
    MaintenanceWorkRequestService,
)
from core.modules.maintenance_management.domain import (
    MaintenanceTaskCompletionRule,
    MaintenancePriority,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderTaskStepStatus,
    MaintenanceWorkOrderType,
)
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org import SiteService
from ui.modules.maintenance_management.shared import (
    build_maintenance_header,
    format_timestamp,
    make_accent_badge,
    make_filter_toggle_button,
    make_meta_badge,
    reset_combo_options,
    selected_combo_value,
    set_filter_panel_visible,
)
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.modules.project_management.dashboard.widgets import KpiCard
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.admin.documents.viewer_dialogs import DocumentPreviewDialog
from ui.platform.shared.guards import make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


_ACTIVE_WORK_ORDER_STATUSES = {
    MaintenanceWorkOrderStatus.PLANNED,
    MaintenanceWorkOrderStatus.WAITING_PARTS,
    MaintenanceWorkOrderStatus.WAITING_APPROVAL,
    MaintenanceWorkOrderStatus.WAITING_SHUTDOWN,
    MaintenanceWorkOrderStatus.SCHEDULED,
    MaintenanceWorkOrderStatus.RELEASED,
    MaintenanceWorkOrderStatus.IN_PROGRESS,
    MaintenanceWorkOrderStatus.PAUSED,
}
_PENDING_CLOSE_STATUSES = {
    MaintenanceWorkOrderStatus.COMPLETED,
    MaintenanceWorkOrderStatus.VERIFIED,
}
_RESPONSIBILITY_ALL = "__ALL__"
_RESPONSIBILITY_EMPLOYEE = "__EMPLOYEE__"
_RESPONSIBILITY_TEAM = "__TEAM__"
_RESPONSIBILITY_UNASSIGNED = "__UNASSIGNED__"
_TASK_ID_ROLE = Qt.UserRole
_STEP_ID_ROLE = Qt.UserRole + 1


class MaintenanceWorkOrdersTab(QWidget):
    def __init__(
        self,
        *,
        work_order_service: MaintenanceWorkOrderService,
        work_order_task_service: MaintenanceWorkOrderTaskService,
        work_order_task_step_service: MaintenanceWorkOrderTaskStepService,
        material_requirement_service: MaintenanceWorkOrderMaterialRequirementService,
        document_service: MaintenanceDocumentService | None = None,
        site_service: SiteService,
        asset_service: MaintenanceAssetService,
        location_service: MaintenanceLocationService,
        system_service: MaintenanceSystemService,
        work_request_service: MaintenanceWorkRequestService | None = None,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._work_order_service = work_order_service
        self._work_order_task_service = work_order_task_service
        self._work_order_task_step_service = work_order_task_step_service
        self._material_requirement_service = material_requirement_service
        self._document_service = document_service
        self._site_service = site_service
        self._asset_service = asset_service
        self._location_service = location_service
        self._system_service = system_service
        self._work_request_service = work_request_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._site_labels: dict[str, str] = {}
        self._asset_labels: dict[str, str] = {}
        self._location_labels: dict[str, str] = {}
        self._system_labels: dict[str, str] = {}
        self._detail_tasks_by_id: dict[str, object] = {}
        self._detail_steps_by_id: dict[str, object] = {}
        self._step_ids_by_task_id: dict[str, list[str]] = {}
        self._detail_documents_by_id: dict[str, object] = {}
        self._setup_ui()
        self.reload_data()
        domain_events.domain_changed.connect(self._on_domain_change)
        domain_events.modules_changed.connect(self._on_modules_changed)
        domain_events.organizations_changed.connect(self._on_organization_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self.context_badge = make_accent_badge("Context: -")
        self.queue_badge = make_meta_badge("0 work orders")
        self.execution_badge = make_meta_badge("0 active")
        build_maintenance_header(
            root=root,
            object_name="maintenanceWorkOrdersHeaderCard",
            eyebrow_text="WORK EXECUTION",
            title_text="Work Orders",
            subtitle_text="Run the corrective and preventive queue, inspect task progress, and follow material readiness from one execution surface.",
            badges=(self.context_badge, self.queue_badge, self.execution_badge),
        )

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceWorkOrdersControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All statuses | All priorities | All types | All responsibilities")
        self.filter_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.filter_summary.setWordWrap(True)
        toolbar_row.addWidget(self.filter_summary, 1)
        self.btn_filters = make_filter_toggle_button(self)
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_refresh.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        toolbar_row.addWidget(self.btn_filters)
        toolbar_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar_row)

        self.filter_panel = QWidget()
        filter_row = QGridLayout(self.filter_panel)
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setHorizontalSpacing(CFG.SPACING_MD)
        filter_row.setVerticalSpacing(CFG.SPACING_SM)
        self.site_combo = QComboBox()
        self.status_combo = QComboBox()
        self.priority_combo = QComboBox()
        self.type_combo = QComboBox()
        self.responsibility_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, title, type, status, failure code, or root cause")
        self.status_combo.addItem("All statuses", None)
        for status in MaintenanceWorkOrderStatus:
            self.status_combo.addItem(status.value.replace("_", " ").title(), status.value)
        self.priority_combo.addItem("All priorities", None)
        for priority in MaintenancePriority:
            self.priority_combo.addItem(priority.value.title(), priority.value)
        self.type_combo.addItem("All types", None)
        for work_order_type in MaintenanceWorkOrderType:
            self.type_combo.addItem(work_order_type.value.replace("_", " ").title(), work_order_type.value)
        self.responsibility_combo.addItem("All responsibilities", _RESPONSIBILITY_ALL)
        self.responsibility_combo.addItem("Employee assigned", _RESPONSIBILITY_EMPLOYEE)
        self.responsibility_combo.addItem("Team assigned", _RESPONSIBILITY_TEAM)
        self.responsibility_combo.addItem("Unassigned", _RESPONSIBILITY_UNASSIGNED)
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Status"), 0, 2)
        filter_row.addWidget(self.status_combo, 0, 3)
        filter_row.addWidget(QLabel("Priority"), 1, 0)
        filter_row.addWidget(self.priority_combo, 1, 1)
        filter_row.addWidget(QLabel("Type"), 1, 2)
        filter_row.addWidget(self.type_combo, 1, 3)
        filter_row.addWidget(QLabel("Responsibility"), 2, 0)
        filter_row.addWidget(self.responsibility_combo, 2, 1)
        filter_row.addWidget(QLabel("Search"), 2, 2)
        filter_row.addWidget(self.search_edit, 2, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Work Orders", "-", "Visible in current queue", CFG.COLOR_ACCENT)
        self.active_card = KpiCard("Active", "-", "Planned through in-progress", CFG.COLOR_SUCCESS)
        self.waiting_parts_card = KpiCard("Waiting Parts", "-", "Blocked by materials", CFG.COLOR_WARNING)
        self.pending_close_card = KpiCard("Pending Close", "-", "Completed or verified", CFG.COLOR_ACCENT)
        for card in (
            self.total_card,
            self.active_card,
            self.waiting_parts_card,
            self.pending_close_card,
        ):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)
        content_row.addWidget(self._build_queue_panel(), 3)
        content_row.addWidget(self._build_detail_panel(), 2)
        root.addLayout(content_row, 1)

        self.site_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self.reload_data)
        )
        self.status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self.reload_work_orders)
        )
        self.priority_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self.reload_work_orders)
        )
        self.type_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self.reload_work_orders)
        )
        self.responsibility_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self.reload_work_orders)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self.reload_work_orders)
        )
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self.reload_data)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.work_order_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._on_work_order_selection_changed)
        )
        self.task_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._on_task_selection_changed)
        )
        self.step_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._on_step_selection_changed)
        )
        self.evidence_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._on_evidence_selection_changed)
        )
        self.btn_preview_evidence.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._show_evidence_preview)
        )

    def _build_queue_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceWorkOrdersQueueSurface",
            alt=False,
        )
        title = QLabel("Work Order Queue")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Corrective, preventive, and operational work ready for planners, supervisors, and technicians.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.work_order_table = build_admin_table(
            headers=("Work Order", "Status", "Priority", "Type", "Site", "Plan Window"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.work_order_table)
        return panel

    def _build_detail_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceWorkOrderDetailSurface",
            alt=False,
        )
        title = QLabel("Selected Work Order")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Execution context, task progress, and material readiness for the selected work order.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.detail_title = QLabel("No work order selected")
        self.detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        layout.addWidget(self.detail_title)
        self.detail_summary = QLabel("Select a work order to inspect execution context, tasks, and material demand.")
        self.detail_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.detail_summary.setWordWrap(True)
        layout.addWidget(self.detail_summary)

        task_title = QLabel("Tasks")
        task_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(task_title)
        self.task_table = build_admin_table(
            headers=("Task", "Assigned", "Status", "Skill", "Minutes", "Steps"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.task_table)

        step_title = QLabel("Task Steps")
        step_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(step_title)
        self.step_table = build_admin_table(
            headers=("Task", "Step", "Status", "Requirements", "Completion"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._stretch(),
                self._stretch(),
            ),
        )
        layout.addWidget(self.step_table)

        execution_title = QLabel("Execution Actions")
        execution_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(execution_title)
        self.execution_summary = QLabel("Select a task or step to run technician execution actions.")
        self.execution_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.execution_summary.setWordWrap(True)
        layout.addWidget(self.execution_summary)
        execution_row = QHBoxLayout()
        execution_row.setSpacing(CFG.SPACING_SM)
        execution_row.addWidget(QLabel("Measurement"))
        self.step_measurement_edit = QLineEdit()
        self.step_measurement_edit.setPlaceholderText("Enter measurement if the selected step requires one")
        execution_row.addWidget(self.step_measurement_edit, 1)
        self.btn_start_step = QPushButton("Start Step")
        self.btn_done_step = QPushButton("Done Step")
        self.btn_confirm_step = QPushButton("Confirm Step")
        self.btn_complete_task = QPushButton("Complete Task")
        for button in (
            self.btn_start_step,
            self.btn_done_step,
            self.btn_confirm_step,
            self.btn_complete_task,
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style("secondary"))
            execution_row.addWidget(button)
        layout.addLayout(execution_row)

        material_title = QLabel("Material Requirements")
        material_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(material_title)
        self.material_table = build_admin_table(
            headers=("Material", "Required", "Issued", "Status", "Source"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.material_table)

        evidence_title = QLabel("Execution Evidence")
        evidence_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(evidence_title)
        self.evidence_summary = QLabel(
            "Linked work-order documents such as procedures, drawings, permits, and completion evidence."
        )
        self.evidence_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.evidence_summary.setWordWrap(True)
        layout.addWidget(self.evidence_summary)
        evidence_action_row = QHBoxLayout()
        evidence_action_row.setSpacing(CFG.SPACING_SM)
        self.btn_preview_evidence = QPushButton("Preview Evidence")
        self.btn_preview_evidence.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_preview_evidence.setStyleSheet(dashboard_action_button_style("secondary"))
        evidence_action_row.addWidget(self.btn_preview_evidence)
        evidence_action_row.addStretch(1)
        layout.addLayout(evidence_action_row)
        self.evidence_table = build_admin_table(
            headers=("Document", "Type", "Structure", "Uploaded"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.evidence_table)
        self.btn_start_step.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._on_start_step)
        )
        self.btn_done_step.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._on_done_step)
        )
        self.btn_confirm_step.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._on_confirm_step)
        )
        self.btn_complete_task.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._on_complete_task)
        )
        self._update_execution_controls()
        self._sync_evidence_actions()
        return panel

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_work_order_id = self._selected_work_order_id()
        try:
            sites = self._site_service.list_sites(active_only=None)
            assets = self._asset_service.list_assets(active_only=None, site_id=selected_site_id)
            systems = self._system_service.list_systems(active_only=None, site_id=selected_site_id)
            locations = self._location_service.list_locations(active_only=None, site_id=selected_site_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Work Orders", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Work Orders", f"Failed to load work-order filters: {exc}")
            return

        self._site_labels = {site.id: site.name for site in sites}
        self._asset_labels = {asset.id: asset.name for asset in assets}
        self._system_labels = {system.id: system.name for system in systems}
        self._location_labels = {location.id: location.name for location in locations}
        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{site.site_code} - {site.name}", site.id) for site in sites],
            selected_value=selected_site_id,
        )
        self.reload_work_orders(selected_work_order_id=selected_work_order_id)

    def reload_work_orders(
        self,
        *,
        selected_work_order_id: str | None = None,
        selected_task_id: str | None = None,
        selected_step_id: str | None = None,
    ) -> None:
        selected_work_order_id = selected_work_order_id or self._selected_work_order_id()
        responsibility_filter = selected_combo_value(self.responsibility_combo) or _RESPONSIBILITY_ALL
        try:
            rows = self._work_order_service.search_work_orders(
                search_text=self.search_edit.text(),
                site_id=selected_combo_value(self.site_combo),
                status=selected_combo_value(self.status_combo),
                priority=selected_combo_value(self.priority_combo),
                work_order_type=selected_combo_value(self.type_combo),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Work Orders", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Work Orders", f"Failed to load maintenance work orders: {exc}")
            return

        if responsibility_filter == _RESPONSIBILITY_EMPLOYEE:
            rows = [row for row in rows if row.assigned_employee_id]
        elif responsibility_filter == _RESPONSIBILITY_TEAM:
            rows = [row for row in rows if row.assigned_team_id]
        elif responsibility_filter == _RESPONSIBILITY_UNASSIGNED:
            rows = [row for row in rows if not row.assigned_employee_id and not row.assigned_team_id]

        self.total_card.set_value(str(len(rows)))
        self.active_card.set_value(str(sum(1 for row in rows if row.status in _ACTIVE_WORK_ORDER_STATUSES)))
        self.waiting_parts_card.set_value(
            str(sum(1 for row in rows if row.status == MaintenanceWorkOrderStatus.WAITING_PARTS))
        )
        self.pending_close_card.set_value(str(sum(1 for row in rows if row.status in _PENDING_CLOSE_STATUSES)))
        self.context_badge.setText(f"Context: {self._context_label()}")
        if responsibility_filter in {_RESPONSIBILITY_EMPLOYEE, _RESPONSIBILITY_TEAM}:
            self.queue_badge.setText(f"{len(rows)} assigned orders")
            self.execution_badge.setText(
                f"{sum(1 for row in rows if row.status == MaintenanceWorkOrderStatus.IN_PROGRESS)} assigned active"
            )
        elif responsibility_filter == _RESPONSIBILITY_UNASSIGNED:
            self.queue_badge.setText(f"{len(rows)} unassigned orders")
            self.execution_badge.setText(
                f"{sum(1 for row in rows if row.status == MaintenanceWorkOrderStatus.IN_PROGRESS)} unassigned active"
            )
        else:
            self.queue_badge.setText(f"{len(rows)} work orders")
            self.execution_badge.setText(
                f"{sum(1 for row in rows if row.status == MaintenanceWorkOrderStatus.IN_PROGRESS)} in progress"
            )
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.status_combo.currentText()} | "
            f"{self.priority_combo.currentText()} | {self.type_combo.currentText()} | {self.responsibility_combo.currentText()}"
            + (
                f" | Search: {self.search_edit.text().strip()}"
                if self.search_edit.text().strip()
                else ""
            )
        )
        self._populate_work_order_table(
            rows,
            selected_work_order_id=selected_work_order_id,
            selected_task_id=selected_task_id,
            selected_step_id=selected_step_id,
        )

    def _populate_work_order_table(
        self,
        rows,
        *,
        selected_work_order_id: str | None,
        selected_task_id: str | None,
        selected_step_id: str | None,
    ) -> None:
        self.work_order_table.blockSignals(True)
        self.work_order_table.setRowCount(len(rows))
        selected_row = 0 if rows else -1
        for row_index, work_order in enumerate(rows):
            values = (
                f"{work_order.work_order_code} - {work_order.title or work_order.work_order_type.value.replace('_', ' ').title()}",
                work_order.status.value.replace("_", " ").title(),
                work_order.priority.value.title(),
                work_order.work_order_type.value.replace("_", " ").title(),
                self._site_labels.get(work_order.site_id, work_order.site_id),
                self._format_plan_window(work_order),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, work_order.id)
                self.work_order_table.setItem(row_index, column, item)
            if selected_work_order_id and work_order.id == selected_work_order_id:
                selected_row = row_index
        if selected_row >= 0:
            self.work_order_table.selectRow(selected_row)
            self.work_order_table.blockSignals(False)
            self._refresh_work_order_details(
                rows[selected_row].id,
                selected_task_id=selected_task_id,
                selected_step_id=selected_step_id,
            )
            return
        self.work_order_table.blockSignals(False)
        self._clear_work_order_details()

    def _refresh_work_order_details(
        self,
        work_order_id: str,
        *,
        selected_task_id: str | None = None,
        selected_step_id: str | None = None,
    ) -> None:
        selected_task_id = selected_task_id or self._selected_task_id()
        selected_step_id = selected_step_id or self._selected_step_id()
        try:
            work_order = self._work_order_service.get_work_order(work_order_id)
            tasks = sorted(
                self._work_order_task_service.list_tasks(work_order_id=work_order.id),
                key=lambda row: row.sequence_no,
            )
            step_rows_by_task_id = {
                task.id: sorted(
                    self._work_order_task_step_service.list_steps(work_order_task_id=task.id),
                    key=lambda row: row.step_number,
                )
                for task in tasks
            }
            materials = self._material_requirement_service.list_requirements(work_order_id=work_order.id)
            documents = (
                self._document_service.list_documents_for_entity(
                    entity_type="work_order",
                    entity_id=work_order.id,
                    active_only=None,
                )
                if self._document_service is not None
                else []
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Work Orders", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Work Orders", f"Failed to load work-order details: {exc}")
            return

        self._detail_tasks_by_id = {task.id: task for task in tasks}
        self._detail_steps_by_id = {}
        self._step_ids_by_task_id = {}
        self._detail_documents_by_id = {document.id: document for document in documents}
        for task in tasks:
            step_ids: list[str] = []
            for step in step_rows_by_task_id.get(task.id, []):
                self._detail_steps_by_id[step.id] = step
                step_ids.append(step.id)
            self._step_ids_by_task_id[task.id] = step_ids

        source_label = self._source_label(work_order.source_type, work_order.source_id)
        flags: list[str] = []
        if work_order.requires_shutdown:
            flags.append("Shutdown")
        if work_order.permit_required:
            flags.append("Permit")
        if work_order.approval_required:
            flags.append("Approval")
        if work_order.is_preventive:
            flags.append("Preventive")
        if work_order.is_emergency:
            flags.append("Emergency")
        flag_text = ", ".join(flags) if flags else "-"

        self.detail_title.setText(
            f"{work_order.work_order_code} - {work_order.title or work_order.work_order_type.value.replace('_', ' ').title()}"
        )
        self.detail_summary.setText(
            "\n".join(
                [
                    f"Type: {work_order.work_order_type.value.replace('_', ' ').title()} | Status: {work_order.status.value.replace('_', ' ').title()} | Priority: {work_order.priority.value.title()}",
                    f"Site: {self._site_labels.get(work_order.site_id, work_order.site_id)}",
                    f"Asset: {self._label_for(self._asset_labels, work_order.asset_id)} | System: {self._label_for(self._system_labels, work_order.system_id)}",
                    f"Location: {self._label_for(self._location_labels, work_order.location_id)} | Component: {work_order.component_id or '-'}",
                    f"Assigned: {self._format_assignment(work_order.assigned_employee_id, work_order.assigned_team_id)} | Planner: {work_order.planner_user_id or '-'} | Supervisor: {work_order.supervisor_user_id or '-'}",
                    f"Source: {source_label}",
                    f"Plan window: {self._format_timestamp_pair(work_order.planned_start, work_order.planned_end)}",
                    f"Actual window: {self._format_timestamp_pair(work_order.actual_start, work_order.actual_end)}",
                    f"Failure / Root cause: {work_order.failure_code or '-'} / {work_order.root_cause_code or '-'}",
                    f"Downtime: {work_order.downtime_minutes or 0} min | Flags: {flag_text}",
                    f"Evidence: {len(documents)} linked document(s)",
                    f"Notes: {work_order.notes or '-'}",
                ]
            )
        )
        self._populate_task_table(
            tasks,
            step_rows_by_task_id=step_rows_by_task_id,
            selected_task_id=selected_task_id,
        )
        self._populate_step_table(
            tasks,
            step_rows_by_task_id=step_rows_by_task_id,
            selected_task_id=selected_task_id,
            selected_step_id=selected_step_id,
        )
        self._populate_material_table(materials)
        self._populate_evidence_table(documents)
        self._sync_step_measurement_editor(self._selected_step())
        self._update_execution_controls()
        self._sync_evidence_actions()

    def _populate_task_table(self, tasks, *, step_rows_by_task_id, selected_task_id: str | None) -> None:
        self.task_table.blockSignals(True)
        self.task_table.setRowCount(len(tasks))
        selected_row = 0 if tasks else -1
        for row_index, task in enumerate(tasks):
            step_rows = step_rows_by_task_id.get(task.id, [])
            done_steps = sum(1 for row in step_rows if row.status.value == "DONE")
            values = (
                f"{task.sequence_no}. {task.task_name}",
                self._format_assignment(task.assigned_employee_id, task.assigned_team_id),
                task.status.value.replace("_", " ").title(),
                task.required_skill or "-",
                self._format_task_minutes(task),
                self._format_step_summary(task.status, done_steps, len(step_rows)),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(_TASK_ID_ROLE, task.id)
                self.task_table.setItem(row_index, column, item)
            if selected_task_id and task.id == selected_task_id:
                selected_row = row_index
        if selected_row >= 0:
            self.task_table.selectRow(selected_row)
        else:
            self.task_table.clearSelection()
        self.task_table.blockSignals(False)

    def _populate_step_table(
        self,
        tasks,
        *,
        step_rows_by_task_id,
        selected_task_id: str | None,
        selected_step_id: str | None,
    ) -> None:
        flattened_rows: list[tuple[object, object]] = []
        for task in tasks:
            for step in step_rows_by_task_id.get(task.id, []):
                flattened_rows.append((task, step))
        self.step_table.blockSignals(True)
        self.step_table.setRowCount(len(flattened_rows))
        selected_row = -1
        for row_index, (task, step) in enumerate(flattened_rows):
            values = (
                f"{task.sequence_no}. {task.task_name}",
                f"{step.step_number}. {step.instruction}",
                step.status.value.replace("_", " ").title(),
                self._format_step_requirements(step),
                self._format_step_completion(step),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(_TASK_ID_ROLE, task.id)
                if column == 1:
                    item.setData(_STEP_ID_ROLE, step.id)
                self.step_table.setItem(row_index, column, item)
            if selected_step_id and step.id == selected_step_id:
                selected_row = row_index
            elif selected_row < 0 and selected_task_id and task.id == selected_task_id:
                selected_row = row_index
        if selected_row >= 0:
            self.step_table.selectRow(selected_row)
        elif flattened_rows:
            self.step_table.selectRow(0)
        else:
            self.step_table.clearSelection()
        self.step_table.blockSignals(False)

    def _populate_material_table(self, materials) -> None:
        self.material_table.setRowCount(len(materials))
        for row_index, requirement in enumerate(materials):
            values = (
                requirement.description or requirement.stock_item_id or "-",
                f"{requirement.required_qty} {requirement.required_uom}",
                f"{requirement.issued_qty} {requirement.required_uom}",
                requirement.procurement_status.value.replace("_", " ").title(),
                "Stock" if requirement.is_stock_item else "Direct",
            )
            for column, value in enumerate(values):
                self.material_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_evidence_table(self, documents) -> None:
        self.evidence_table.blockSignals(True)
        self.evidence_table.setRowCount(len(documents))
        for row_index, document in enumerate(documents):
            values = (
                f"{document.document_code} - {document.title}",
                document.document_type.value.replace("_", " ").title(),
                document.document_structure_id or "-",
                format_timestamp(document.uploaded_at),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, document.id)
                self.evidence_table.setItem(row_index, column, item)
        if documents:
            self.evidence_table.selectRow(0)
        else:
            self.evidence_table.clearSelection()
        self.evidence_table.blockSignals(False)
        count_text = f"{len(documents)} linked document(s)" if documents else "No work-order evidence linked yet."
        self.evidence_summary.setText(
            "Linked work-order documents such as procedures, drawings, permits, and completion evidence. "
            f"Current selection: {count_text}"
        )

    def _on_work_order_selection_changed(self) -> None:
        work_order_id = self._selected_work_order_id()
        if work_order_id:
            self._refresh_work_order_details(work_order_id)
            return
        self._clear_work_order_details()

    def _on_task_selection_changed(self) -> None:
        task_id = self._selected_task_id()
        if task_id:
            current_step = self._selected_step()
            if current_step is None or current_step.work_order_task_id != task_id:
                self._select_first_step_for_task(task_id)
        self._sync_step_measurement_editor(self._selected_step())
        self._update_execution_controls()

    def _on_step_selection_changed(self) -> None:
        step = self._selected_step()
        if step is not None:
            self._select_task_row(step.work_order_task_id)
        self._sync_step_measurement_editor(step)
        self._update_execution_controls()

    def _clear_work_order_details(self) -> None:
        self.detail_title.setText("No work order selected")
        self.detail_summary.setText("Select a work order to inspect execution context, tasks, and material demand.")
        self._detail_tasks_by_id = {}
        self._detail_steps_by_id = {}
        self._step_ids_by_task_id = {}
        self._detail_documents_by_id = {}
        self.task_table.setRowCount(0)
        self.step_table.setRowCount(0)
        self.material_table.setRowCount(0)
        self.evidence_table.setRowCount(0)
        self.step_measurement_edit.clear()
        self._update_execution_controls()
        self._sync_evidence_actions()

    def _selected_work_order_id(self) -> str | None:
        row = self.work_order_table.currentRow()
        if row < 0:
            return None
        item = self.work_order_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_task_id(self) -> str | None:
        row = self.task_table.currentRow()
        if row < 0:
            return None
        item = self.task_table.item(row, 0)
        if item is None:
            return None
        value = item.data(_TASK_ID_ROLE)
        return str(value) if value else None

    def _selected_step_id(self) -> str | None:
        row = self.step_table.currentRow()
        if row < 0:
            return None
        item = self.step_table.item(row, 1)
        if item is None:
            return None
        value = item.data(_STEP_ID_ROLE)
        return str(value) if value else None

    def _selected_task(self):
        task_id = self._selected_task_id()
        if not task_id:
            return None
        return self._detail_tasks_by_id.get(task_id)

    def _selected_step(self):
        step_id = self._selected_step_id()
        if not step_id:
            return None
        return self._detail_steps_by_id.get(step_id)

    def _selected_evidence_document(self):
        row = self.evidence_table.currentRow()
        if row < 0:
            return None
        item = self.evidence_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        if not value:
            return None
        return self._detail_documents_by_id.get(str(value))

    def _select_task_row(self, task_id: str) -> None:
        current_task_id = self._selected_task_id()
        if current_task_id == task_id:
            return
        for row in range(self.task_table.rowCount()):
            item = self.task_table.item(row, 0)
            if item is not None and item.data(_TASK_ID_ROLE) == task_id:
                self.task_table.blockSignals(True)
                self.task_table.selectRow(row)
                self.task_table.blockSignals(False)
                break

    def _select_first_step_for_task(self, task_id: str) -> None:
        for row in range(self.step_table.rowCount()):
            task_item = self.step_table.item(row, 0)
            if task_item is not None and task_item.data(_TASK_ID_ROLE) == task_id:
                self.step_table.blockSignals(True)
                self.step_table.selectRow(row)
                self.step_table.blockSignals(False)
                return
        self.step_table.blockSignals(True)
        self.step_table.clearSelection()
        self.step_table.blockSignals(False)

    def _task_can_complete(self, task) -> bool:
        if task.status not in {
            MaintenanceWorkOrderTaskStatus.NOT_STARTED,
            MaintenanceWorkOrderTaskStatus.IN_PROGRESS,
        }:
            return False
        if task.completion_rule != MaintenanceTaskCompletionRule.ALL_STEPS_REQUIRED:
            return True
        step_ids = self._step_ids_by_task_id.get(task.id, [])
        if not step_ids:
            return False
        for step_id in step_ids:
            step = self._detail_steps_by_id.get(step_id)
            if step is None or step.status != MaintenanceWorkOrderTaskStepStatus.DONE:
                return False
            if step.requires_confirmation and step.confirmed_at is None:
                return False
            if step.requires_measurement and not str(step.measurement_value or "").strip():
                return False
        return True

    def _sync_step_measurement_editor(self, step) -> None:
        if step is None:
            self.step_measurement_edit.clear()
            self.step_measurement_edit.setPlaceholderText("Enter measurement if the selected step requires one")
            return
        if step.requires_measurement or step.measurement_value:
            unit = f" ({step.measurement_unit})" if step.measurement_unit else ""
            self.step_measurement_edit.setPlaceholderText(f"Measurement{unit}")
            self.step_measurement_edit.setText(step.measurement_value or "")
            return
        self.step_measurement_edit.clear()
        self.step_measurement_edit.setPlaceholderText("Selected step does not require a measurement")

    def _update_execution_controls(self) -> None:
        task = self._selected_task()
        step = self._selected_step()
        if step is None and task is None:
            self.execution_summary.setText("Select a task or step to run technician execution actions.")
            self.step_measurement_edit.setEnabled(False)
            self.btn_start_step.setEnabled(False)
            self.btn_done_step.setEnabled(False)
            self.btn_confirm_step.setEnabled(False)
            self.btn_complete_task.setEnabled(False)
            return
        if step is not None:
            requirement_bits: list[str] = []
            if step.requires_measurement:
                unit = f" ({step.measurement_unit})" if step.measurement_unit else ""
                requirement_bits.append(f"measurement{unit}")
            if step.requires_confirmation:
                requirement_bits.append("confirmation")
            if step.requires_photo:
                requirement_bits.append("photo evidence")
            requirement_text = ", ".join(requirement_bits) if requirement_bits else "standard execution"
            self.execution_summary.setText(
                f"Selected step {step.step_number} is {step.status.value.replace('_', ' ').title()}. "
                f"Requirements: {requirement_text}."
            )
            self.step_measurement_edit.setEnabled(
                step.requires_measurement
                and step.status not in {
                    MaintenanceWorkOrderTaskStepStatus.DONE,
                    MaintenanceWorkOrderTaskStepStatus.SKIPPED,
                }
            )
        elif task is not None:
            self.execution_summary.setText(
                f"Selected task {task.sequence_no} is {task.status.value.replace('_', ' ').title()}. "
                "Choose a step to drive execution or complete the task when all required steps are done."
            )
            self.step_measurement_edit.setEnabled(False)
        self.btn_start_step.setEnabled(
            step is not None
            and step.status in {
                MaintenanceWorkOrderTaskStepStatus.NOT_STARTED,
                MaintenanceWorkOrderTaskStepStatus.FAILED,
            }
        )
        self.btn_done_step.setEnabled(
            step is not None
            and step.status in {
                MaintenanceWorkOrderTaskStepStatus.NOT_STARTED,
                MaintenanceWorkOrderTaskStepStatus.IN_PROGRESS,
            }
        )
        self.btn_confirm_step.setEnabled(
            step is not None
            and step.requires_confirmation
            and step.status == MaintenanceWorkOrderTaskStepStatus.DONE
            and step.confirmed_at is None
        )
        self.btn_complete_task.setEnabled(task is not None and self._task_can_complete(task))

    def _reload_after_execution(self, *, work_order_id: str, task_id: str | None, step_id: str | None) -> None:
        self.reload_work_orders(
            selected_work_order_id=work_order_id,
            selected_task_id=task_id,
            selected_step_id=step_id,
        )

    def _on_start_step(self) -> None:
        step = self._selected_step()
        task = self._selected_task()
        work_order_id = self._selected_work_order_id()
        if step is None or task is None or work_order_id is None:
            QMessageBox.information(self, "Maintenance Work Orders", "Select a task step to start execution.")
            return
        updated = self._work_order_task_step_service.update_step(
            step.id,
            status=MaintenanceWorkOrderTaskStepStatus.IN_PROGRESS.value,
            expected_version=step.version,
        )
        self._reload_after_execution(work_order_id=work_order_id, task_id=task.id, step_id=updated.id)

    def _on_done_step(self) -> None:
        step = self._selected_step()
        task = self._selected_task()
        work_order_id = self._selected_work_order_id()
        if step is None or task is None or work_order_id is None:
            QMessageBox.information(self, "Maintenance Work Orders", "Select a task step to complete it.")
            return
        update_kwargs = {
            "status": MaintenanceWorkOrderTaskStepStatus.DONE.value,
            "expected_version": step.version,
        }
        if self.step_measurement_edit.text().strip():
            update_kwargs["measurement_value"] = self.step_measurement_edit.text().strip()
        updated = self._work_order_task_step_service.update_step(step.id, **update_kwargs)
        self._reload_after_execution(work_order_id=work_order_id, task_id=task.id, step_id=updated.id)

    def _on_confirm_step(self) -> None:
        step = self._selected_step()
        task = self._selected_task()
        work_order_id = self._selected_work_order_id()
        if step is None or task is None or work_order_id is None:
            QMessageBox.information(self, "Maintenance Work Orders", "Select a completed task step to confirm it.")
            return
        updated = self._work_order_task_step_service.update_step(
            step.id,
            confirm_completion=True,
            expected_version=step.version,
        )
        self._reload_after_execution(work_order_id=work_order_id, task_id=task.id, step_id=updated.id)

    def _on_complete_task(self) -> None:
        task = self._selected_task()
        step_id = self._selected_step_id()
        work_order_id = self._selected_work_order_id()
        if task is None or work_order_id is None:
            QMessageBox.information(self, "Maintenance Work Orders", "Select a task to complete it.")
            return
        updated = self._work_order_task_service.update_task(
            task.id,
            status=MaintenanceWorkOrderTaskStatus.COMPLETED.value,
            expected_version=task.version,
        )
        self._reload_after_execution(work_order_id=work_order_id, task_id=updated.id, step_id=step_id)

    def _on_evidence_selection_changed(self) -> None:
        self._sync_evidence_actions()

    def _sync_evidence_actions(self) -> None:
        self.btn_preview_evidence.setEnabled(self._selected_evidence_document() is not None)

    def _show_evidence_preview(self) -> None:
        document = self._selected_evidence_document()
        if document is None:
            QMessageBox.information(self, "Maintenance Work Orders", "Select a linked evidence document to preview it.")
            return
        DocumentPreviewDialog(document=document, parent=self).exec()

    def _source_label(self, source_type: str, source_id: str | None) -> str:
        if not source_id:
            return source_type.replace("_", " ").title()
        if source_type == "WORK_REQUEST" and self._work_request_service is not None:
            try:
                request = self._work_request_service.get_work_request(source_id)
            except Exception:  # noqa: BLE001
                return f"{source_type.replace('_', ' ').title()}: {source_id}"
            return f"Work Request: {request.work_request_code}"
        return f"{source_type.replace('_', ' ').title()}: {source_id}"

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

    def _on_domain_change(self, event: DomainChangeEvent) -> None:
        if getattr(event, "scope_code", "") == "maintenance_management":
            self.reload_data()

    def _on_modules_changed(self, _module_code: str) -> None:
        self.reload_data()

    def _on_organization_changed(self, _organization_id: str) -> None:
        self.reload_data()

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    @staticmethod
    def _label_for(labels: dict[str, str], value: str | None) -> str:
        if not value:
            return "-"
        return labels.get(value, value)

    @staticmethod
    def _format_plan_window(work_order) -> str:
        if work_order.planned_start is None and work_order.planned_end is None:
            return "-"
        return MaintenanceWorkOrdersTab._format_timestamp_pair(
            work_order.planned_start,
            work_order.planned_end,
        )

    @staticmethod
    def _format_timestamp_pair(start, end) -> str:
        if start is None and end is None:
            return "-"
        if start is None:
            return f"Until {format_timestamp(end)}"
        if end is None:
            return f"From {format_timestamp(start)}"
        return f"{format_timestamp(start)} -> {format_timestamp(end)}"

    @staticmethod
    def _format_task_minutes(task) -> str:
        estimated = task.estimated_minutes if task.estimated_minutes is not None else "-"
        actual = task.actual_minutes if task.actual_minutes is not None else "-"
        return f"{estimated} / {actual}"

    @staticmethod
    def _format_step_summary(task_status: MaintenanceWorkOrderTaskStatus, done_steps: int, total_steps: int) -> str:
        if total_steps == 0:
            return "No steps"
        if task_status == MaintenanceWorkOrderTaskStatus.COMPLETED:
            return f"{done_steps}/{total_steps} done"
        return f"{done_steps}/{total_steps} complete"

    @staticmethod
    def _format_assignment(assigned_employee_id: str | None, assigned_team_id: str | None) -> str:
        if assigned_employee_id:
            return f"Employee {assigned_employee_id}"
        if assigned_team_id:
            return f"Team {assigned_team_id}"
        return "Unassigned"

    @staticmethod
    def _format_step_requirements(step) -> str:
        flags = []
        if step.requires_confirmation:
            flags.append("Confirm")
        if step.requires_measurement:
            unit = f" {step.measurement_unit}" if step.measurement_unit else ""
            flags.append(f"Measure{unit}")
        if step.requires_photo:
            flags.append("Photo")
        return ", ".join(flags) if flags else "Standard"

    @staticmethod
    def _format_step_completion(step) -> str:
        parts = []
        if step.completed_at is not None:
            completed_by = f" by {step.completed_by_user_id}" if step.completed_by_user_id else ""
            parts.append(f"Done {format_timestamp(step.completed_at)}{completed_by}")
        if step.confirmed_at is not None:
            confirmed_by = f" by {step.confirmed_by_user_id}" if step.confirmed_by_user_id else ""
            parts.append(f"Confirmed {format_timestamp(step.confirmed_at)}{confirmed_by}")
        if step.measurement_value:
            measurement_unit = f" {step.measurement_unit}" if step.measurement_unit else ""
            parts.append(f"Measurement {step.measurement_value}{measurement_unit}")
        return " | ".join(parts) if parts else "-"

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceWorkOrdersTab"]
