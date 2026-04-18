from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenancePreventiveGenerationService,
    MaintenancePreventivePlanService,
    MaintenanceReliabilityService,
    MaintenanceSensorExceptionService,
    MaintenanceSystemService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderService,
    MaintenanceWorkRequestService,
)
from src.core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org import SiteService
from ui.modules.maintenance_management.shared import (
    MaintenanceWorkbenchNavigator,
    MaintenanceWorkbenchSection,
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
from ui.platform.shared.guards import make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


_OPEN_REQUEST_STATUS = "__OPEN__"
_BACKLOG_WORK_ORDER_STATUS = "__BACKLOG__"
_CLOSED_ORDER_STATUSES = {"COMPLETED", "VERIFIED", "CLOSED", "CANCELLED"}
_OPEN_REQUEST_STATUSES = {"NEW", "TRIAGED", "APPROVED", "DEFERRED"}
_MATERIAL_RISK_STATUSES = {"PLANNED", "SHORTAGE_IDENTIFIED", "REQUISITIONED", "PARTIALLY_ISSUED", "NON_STOCK"}
_PREVENTIVE_DUE_SOON_WINDOW = timedelta(days=30)


@dataclass(frozen=True)
class _PlannerPreventiveRow:
    plan_id: str
    plan_code: str
    plan_name: str
    anchor_label: str
    due_state: str
    due_reason: str
    generation_target: str
    trigger_label: str
    next_due_at: datetime | None
    next_due_counter: int | None
    next_due_label: str
    is_due_soon: bool


class MaintenancePlannerTab(QWidget):
    def __init__(
        self,
        *,
        work_request_service: MaintenanceWorkRequestService,
        work_order_service: MaintenanceWorkOrderService,
        material_requirement_service: MaintenanceWorkOrderMaterialRequirementService,
        preventive_plan_service: MaintenancePreventivePlanService,
        preventive_generation_service: MaintenancePreventiveGenerationService,
        reliability_service: MaintenanceReliabilityService,
        sensor_exception_service: MaintenanceSensorExceptionService,
        site_service: SiteService,
        asset_service: MaintenanceAssetService,
        system_service: MaintenanceSystemService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._work_request_service = work_request_service
        self._work_order_service = work_order_service
        self._material_requirement_service = material_requirement_service
        self._preventive_plan_service = preventive_plan_service
        self._preventive_generation_service = preventive_generation_service
        self._reliability_service = reliability_service
        self._sensor_exception_service = sensor_exception_service
        self._site_service = site_service
        self._asset_service = asset_service
        self._system_service = system_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._site_labels: dict[str, str] = {}
        self._asset_labels: dict[str, str] = {}
        self._system_labels: dict[str, str] = {}
        self._request_rows = []
        self._work_order_rows = []
        self._material_risk_rows = []
        self._preventive_rows: list[_PlannerPreventiveRow] = []
        self._recurring_rows = []
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
        self.backlog_badge = make_meta_badge("0 backlog orders")
        self.preventive_badge = make_meta_badge("0 preventive reviews")
        self.material_badge = make_meta_badge("0 material risks")
        build_maintenance_header(
            root=root,
            object_name="maintenancePlannerHeaderCard",
            eyebrow_text="PLANNER WORKBENCH",
            title_text="Planner",
            subtitle_text="Coordinate intake, backlog, preventive readiness, material planning, and recurring failure priorities from one maintenance planning surface.",
            badges=(self.context_badge, self.backlog_badge, self.preventive_badge, self.material_badge),
        )

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenancePlannerControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All assets | All systems | Open requests | Backlog orders")
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
        self.asset_combo = QComboBox()
        self.system_combo = QComboBox()
        self.request_status_combo = QComboBox()
        self.work_order_status_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, title, failure, source, or planner context")
        self.request_status_combo.addItem("Open requests", _OPEN_REQUEST_STATUS)
        self.request_status_combo.addItem("All request statuses", None)
        for label in ("NEW", "TRIAGED", "APPROVED", "REJECTED", "CONVERTED", "DEFERRED"):
            self.request_status_combo.addItem(label.replace("_", " ").title(), label)
        self.work_order_status_combo.addItem("Backlog orders", _BACKLOG_WORK_ORDER_STATUS)
        self.work_order_status_combo.addItem("All work orders", None)
        for label in (
            "PLANNED",
            "WAITING_PARTS",
            "WAITING_APPROVAL",
            "WAITING_SHUTDOWN",
            "SCHEDULED",
            "RELEASED",
            "IN_PROGRESS",
            "PAUSED",
            "COMPLETED",
            "VERIFIED",
            "CLOSED",
            "CANCELLED",
        ):
            self.work_order_status_combo.addItem(label.replace("_", " ").title(), label)
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Asset"), 0, 2)
        filter_row.addWidget(self.asset_combo, 0, 3)
        filter_row.addWidget(QLabel("System"), 1, 0)
        filter_row.addWidget(self.system_combo, 1, 1)
        filter_row.addWidget(QLabel("Request queue"), 1, 2)
        filter_row.addWidget(self.request_status_combo, 1, 3)
        filter_row.addWidget(QLabel("Work-order queue"), 2, 0)
        filter_row.addWidget(self.work_order_status_combo, 2, 1)
        filter_row.addWidget(QLabel("Search"), 2, 2)
        filter_row.addWidget(self.search_edit, 2, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.request_card = KpiCard("Open Requests", "-", "Intake still needing planner attention", CFG.COLOR_ACCENT)
        self.backlog_card = KpiCard("Backlog Orders", "-", "Orders still in planning or execution queues", CFG.COLOR_WARNING)
        self.preventive_card = KpiCard("Preventive Review", "-", "Due, due-soon, and blocked preventive plans", CFG.COLOR_ACCENT)
        self.material_card = KpiCard("Material Risks", "-", "Requirements not yet fully ready", CFG.COLOR_SUCCESS)
        self.recurring_card = KpiCard("Recurring Patterns", "-", "Failure patterns to review while planning", CFG.COLOR_ACCENT)
        for card in (self.request_card, self.backlog_card, self.preventive_card, self.material_card, self.recurring_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        self.workbench = MaintenanceWorkbenchNavigator(object_name="maintenancePlannerWorkbench", parent=self)
        self.request_panel = self._build_request_panel()
        self.work_order_panel = self._build_work_order_panel()
        self.material_panel = self._build_material_panel()
        self.preventive_panel = self._build_preventive_panel()
        self.recurring_panel = self._build_recurring_panel()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(
                    key="request_intake",
                    label="Request Intake",
                    widget=self.request_panel,
                ),
                MaintenanceWorkbenchSection(
                    key="backlog",
                    label="Backlog and Scheduling",
                    widget=self.work_order_panel,
                ),
                MaintenanceWorkbenchSection(
                    key="material_readiness",
                    label="Material Readiness",
                    widget=self.material_panel,
                ),
                MaintenanceWorkbenchSection(
                    key="preventive_readiness",
                    label="Preventive Readiness",
                    widget=self.preventive_panel,
                ),
                MaintenanceWorkbenchSection(
                    key="recurring_failure_review",
                    label="Recurring Failure Review",
                    widget=self.recurring_panel,
                ),
            ],
            initial_key="request_intake",
        )
        root.addWidget(self.workbench, 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.asset_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Planner", callback=self.reload_planning_data)
        )
        self.system_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Planner", callback=self.reload_planning_data)
        )
        self.request_status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Planner", callback=self.reload_planning_data)
        )
        self.work_order_status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Planner", callback=self.reload_planning_data)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Maintenance Planner", callback=self.reload_planning_data)
        )
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Planner", callback=self.reload_data)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)

    def _build_request_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenancePlannerRequestSurface",
            alt=False,
        )
        #title = QLabel("Request Intake")
        #title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Requests still needing triage, approval, or conversion decisions.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        #layout.addWidget(title)
        layout.addWidget(subtitle)
        self.request_table = build_admin_table(
            headers=("Request", "Anchor", "Status", "Priority"),
            resize_modes=(self._stretch(), self._stretch(), self._resize_to_contents(), self._resize_to_contents()),
        )
        layout.addWidget(self.request_table)
        return panel

    def _build_work_order_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenancePlannerBacklogSurface",
            alt=False,
        )
        #title = QLabel("Backlog and Scheduling")
        #title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Corrective and preventive work orders that still need planning, parts, or scheduling decisions.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        #layout.addWidget(title)
        layout.addWidget(subtitle)
        self.work_order_table = build_admin_table(
            headers=("Work Order", "Type", "Status", "Priority", "Plan Window"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._stretch(),
            ),
        )
        layout.addWidget(self.work_order_table)
        return panel

    def _build_material_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenancePlannerMaterialSurface",
            alt=False,
        )
        #title = QLabel("Material Readiness")
        #title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Material lines that may block scheduled work or need procurement follow-through.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        #layout.addWidget(title)
        layout.addWidget(subtitle)
        self.material_table = build_admin_table(
            headers=("Work Order", "Material", "Status", "Qty", "Storeroom"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.material_table)
        return panel

    def _build_recurring_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenancePlannerRecurringSurface",
            alt=False,
        )
        #title = QLabel("Recurring Failure Review")
        #title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Recurring-failure and exception signals that planners should fold into scheduling decisions.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        #layout.addWidget(title)
        layout.addWidget(subtitle)
        self.recurring_table = build_admin_table(
            headers=("Anchor", "Failure", "Lead Cause", "Count", "Open", "Sensor Exceptions"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.recurring_table)
        return panel

    def _build_preventive_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenancePlannerPreventiveSurface",
            alt=False,
        )
        #title = QLabel("Preventive Readiness")
        #title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Due, near-due, and blocked preventive plans that planners should fold into the active schedule.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        #layout.addWidget(title)
        layout.addWidget(subtitle)
        self.preventive_table = build_admin_table(
            headers=("Plan", "Trigger", "Due State", "Next Due", "Target"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.preventive_table)
        return panel

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_asset_id = selected_combo_value(self.asset_combo)
        selected_system_id = selected_combo_value(self.system_combo)
        try:
            sites = self._site_service.list_sites(active_only=None)
            assets = self._asset_service.list_assets(active_only=None, site_id=selected_site_id)
            systems = self._system_service.list_systems(active_only=None, site_id=selected_site_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Planner", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Planner", f"Failed to load planner filters: {exc}")
            return

        self._site_labels = {row.id: row.name for row in sites}
        self._asset_labels = {row.id: f"{row.asset_code} - {row.name}" for row in assets}
        self._system_labels = {row.id: f"{row.system_code} - {row.name}" for row in systems}
        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{row.site_code} - {row.name}", row.id) for row in sites],
            selected_value=selected_site_id,
        )
        reset_combo_options(
            self.asset_combo,
            placeholder="All assets",
            options=[(label, row_id) for row_id, label in self._asset_labels.items()],
            selected_value=selected_asset_id,
        )
        reset_combo_options(
            self.system_combo,
            placeholder="All systems",
            options=[(label, row_id) for row_id, label in self._system_labels.items()],
            selected_value=selected_system_id,
        )
        self.reload_planning_data()

    def reload_planning_data(self) -> None:
        search_text = self.search_edit.text().strip().lower()
        site_id = selected_combo_value(self.site_combo)
        asset_id = selected_combo_value(self.asset_combo)
        system_id = selected_combo_value(self.system_combo)
        request_status_value = selected_combo_value(self.request_status_combo)
        work_order_status_value = selected_combo_value(self.work_order_status_combo)
        try:
            request_rows = self._work_request_service.list_work_requests(
                site_id=site_id,
                asset_id=asset_id,
                system_id=system_id,
            )
            work_order_rows = self._work_order_service.list_work_orders(
                site_id=site_id,
                asset_id=asset_id,
                system_id=system_id,
            )
            requirement_rows = self._material_requirement_service.list_requirements()
            preventive_plans = self._preventive_plan_service.search_preventive_plans(
                search_text=self.search_edit.text(),
                active_only=None,
                site_id=site_id,
                asset_id=asset_id,
                system_id=system_id,
            )
            preventive_candidates = self._preventive_generation_service.list_due_candidates(site_id=site_id)
            try:
                recurring_rows = self._reliability_service.list_recurring_failure_patterns(
                    site_id=site_id,
                    asset_id=asset_id,
                    system_id=system_id,
                    min_occurrences=2,
                    limit=10,
                )
            except BusinessRuleError:
                recurring_rows = []
            try:
                exception_rows = self._sensor_exception_service.list_exceptions(status="OPEN")
            except BusinessRuleError:
                exception_rows = []
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Planner", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Planner", f"Failed to load planner queues: {exc}")
            return

        if request_status_value == _OPEN_REQUEST_STATUS:
            request_rows = [row for row in request_rows if row.status.value in _OPEN_REQUEST_STATUSES]
        elif request_status_value:
            request_rows = [row for row in request_rows if row.status.value == request_status_value]
        if work_order_status_value == _BACKLOG_WORK_ORDER_STATUS:
            work_order_rows = [row for row in work_order_rows if row.status.value not in _CLOSED_ORDER_STATUSES]
        elif work_order_status_value:
            work_order_rows = [row for row in work_order_rows if row.status.value == work_order_status_value]

        if search_text:
            request_rows = [row for row in request_rows if search_text in self._request_search_blob(row)]
            work_order_rows = [row for row in work_order_rows if search_text in self._work_order_search_blob(row)]

        work_order_by_id = {row.id: row for row in work_order_rows}
        preventive_candidate_by_id = {row.plan_id: row for row in preventive_candidates}
        self._preventive_rows = sorted(
            (
                self._build_preventive_row(row, preventive_candidate_by_id.get(row.id))
                for row in preventive_plans
            ),
            key=self._preventive_sort_key,
        )
        self._material_risk_rows = [
            row
            for row in requirement_rows
            if row.work_order_id in work_order_by_id and row.procurement_status.value in _MATERIAL_RISK_STATUSES
        ]
        self._request_rows = request_rows
        self._work_order_rows = work_order_rows
        self._recurring_rows = recurring_rows

        exception_count_by_anchor: dict[str, int] = {}
        for row in exception_rows:
            anchor_id = row.sensor_id or row.integration_source_id or ""
            if anchor_id:
                exception_count_by_anchor[anchor_id] = exception_count_by_anchor.get(anchor_id, 0) + 1

        self.request_card.set_value(str(len(self._request_rows)))
        self.backlog_card.set_value(str(len(self._work_order_rows)))
        self.preventive_card.set_value(str(len(self._preventive_rows)))
        self.material_card.set_value(str(len(self._material_risk_rows)))
        self.recurring_card.set_value(str(len(self._recurring_rows)))
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.backlog_badge.setText(f"{len(self._work_order_rows)} backlog orders")
        self.preventive_badge.setText(f"{len(self._preventive_rows)} preventive reviews")
        self.material_badge.setText(f"{len(self._material_risk_rows)} material risks")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.asset_combo.currentText()} | {self.system_combo.currentText()} | "
            f"{self.request_status_combo.currentText()} | {self.work_order_status_combo.currentText()}"
            + (f" | Search: {self.search_edit.text().strip()}" if self.search_edit.text().strip() else "")
        )
        self._populate_request_table()
        self._populate_work_order_table()
        self._populate_material_table(work_order_by_id)
        self._populate_preventive_table()
        self._populate_recurring_table(exception_count_by_anchor)

    def _populate_request_table(self) -> None:
        self.request_table.setRowCount(len(self._request_rows))
        for row_index, row in enumerate(self._request_rows):
            values = (
                f"{row.work_request_code} - {row.title}",
                self._anchor_label(row.asset_id, row.system_id, row.location_id, row.site_id),
                row.status.value.title(),
                row.priority.value.title(),
            )
            for column, value in enumerate(values):
                self.request_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_work_order_table(self) -> None:
        self.work_order_table.setRowCount(len(self._work_order_rows))
        for row_index, row in enumerate(self._work_order_rows):
            values = (
                f"{row.work_order_code} - {row.title}",
                row.work_order_type.value.replace("_", " ").title(),
                row.status.value.replace("_", " ").title(),
                row.priority.value.title(),
                self._format_window(row.planned_start, row.planned_end),
            )
            for column, value in enumerate(values):
                self.work_order_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_material_table(self, work_order_by_id: dict[str, object]) -> None:
        self.material_table.setRowCount(len(self._material_risk_rows))
        for row_index, row in enumerate(self._material_risk_rows):
            work_order = work_order_by_id.get(row.work_order_id)
            values = (
                f"{work_order.work_order_code} - {work_order.title}" if work_order is not None else row.work_order_id,
                row.description,
                row.procurement_status.value.replace("_", " ").title(),
                f"{row.issued_qty}/{row.required_qty} {row.required_uom}",
                row.preferred_storeroom_id or "-",
            )
            for column, value in enumerate(values):
                self.material_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _populate_recurring_table(self, exception_count_by_anchor: dict[str, int]) -> None:
        self.recurring_table.setRowCount(len(self._recurring_rows))
        for row_index, row in enumerate(self._recurring_rows):
            values = (
                f"{row.anchor_code} - {row.anchor_name}",
                row.failure_name,
                row.leading_root_cause_name or "-",
                str(row.occurrence_count),
                str(row.open_work_orders),
                str(exception_count_by_anchor.get(row.anchor_id, 0)),
            )
            for column, value in enumerate(values):
                self.recurring_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_preventive_table(self) -> None:
        self.preventive_table.setRowCount(len(self._preventive_rows))
        for row_index, row in enumerate(self._preventive_rows):
            values = (
                f"{row.plan_code} - {row.plan_name}",
                row.trigger_label,
                self._planner_due_state_label(row),
                row.next_due_label,
                row.generation_target.replace("_", " ").title(),
            )
            for column, value in enumerate(values):
                self.preventive_table.setItem(row_index, column, QTableWidgetItem(value))

    def _anchor_label(self, asset_id: str | None, system_id: str | None, location_id: str | None, site_id: str) -> str:
        if asset_id:
            return self._asset_labels.get(asset_id, asset_id)
        if system_id:
            return self._system_labels.get(system_id, system_id)
        if location_id:
            return location_id
        return self._site_labels.get(site_id, site_id)

    def _build_preventive_row(self, plan, candidate) -> _PlannerPreventiveRow:
        due_state = "NOT_DUE"
        due_reason = "Preventive plan is not currently due."
        generation_target = "WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST"
        if not plan.is_active or plan.status.value != "ACTIVE":
            due_state = "INACTIVE"
            due_reason = "Preventive plan is not active for due generation."
        elif candidate is not None:
            due_state = candidate.due_state
            due_reason = candidate.due_reason
            generation_target = candidate.generation_target

        next_due_at = self._ensure_utc_datetime(plan.next_due_at)
        is_due_soon = (
            due_state == "NOT_DUE"
            and next_due_at is not None
            and datetime.now(timezone.utc) <= next_due_at <= datetime.now(timezone.utc) + _PREVENTIVE_DUE_SOON_WINDOW
        )
        next_due_label = "-"
        if next_due_at is not None:
            next_due_label = format_timestamp(next_due_at)
        elif plan.next_due_counter is not None:
            next_due_label = str(plan.next_due_counter)
        elif due_state == "BLOCKED":
            next_due_label = "Review exception"
        return _PlannerPreventiveRow(
            plan_id=plan.id,
            plan_code=plan.plan_code,
            plan_name=plan.name,
            anchor_label=self._anchor_label(plan.asset_id, plan.system_id, None, plan.site_id),
            due_state=due_state,
            due_reason=due_reason,
            generation_target=generation_target,
            trigger_label=self._planner_trigger_label(plan),
            next_due_at=next_due_at,
            next_due_counter=plan.next_due_counter,
            next_due_label=next_due_label,
            is_due_soon=is_due_soon,
        )

    @staticmethod
    def _ensure_utc_datetime(value:datetime):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _planner_trigger_label(self, plan) -> str:
        if plan.trigger_mode.value == "CALENDAR":
            if plan.calendar_frequency_unit is None or plan.calendar_frequency_value in (None, 0):
                return "Calendar"
            return f"Every {plan.calendar_frequency_value} {plan.calendar_frequency_unit.value.replace('_', ' ').lower()}"
        if plan.trigger_mode.value == "SENSOR":
            return "Sensor threshold"
        return "Hybrid"

    @staticmethod
    def _planner_due_state_label(row: _PlannerPreventiveRow) -> str:
        if row.is_due_soon:
            return "Due Soon"
        return row.due_state.replace("_", " ").title()

    @staticmethod
    def _preventive_sort_key(row: _PlannerPreventiveRow) -> tuple[int, datetime, int, str]:
        if row.due_state == "DUE":
            priority = 0
        elif row.due_state == "BLOCKED":
            priority = 1
        elif row.is_due_soon:
            priority = 2
        elif row.due_state == "NOT_DUE":
            priority = 3
        else:
            priority = 4
        next_due_at = row.next_due_at or datetime.max.replace(tzinfo=timezone.utc)
        next_due_counter = row.next_due_counter if row.next_due_counter is not None else 999999999
        return (priority, next_due_at, next_due_counter, row.plan_code)

    @staticmethod
    def _request_search_blob(row) -> str:
        return " ".join(
            filter(
                None,
                [
                    row.work_request_code,
                    row.title,
                    row.description,
                    row.failure_symptom_code,
                    row.request_type,
                    row.status.value,
                ],
            )
        ).lower()

    @staticmethod
    def _work_order_search_blob(row) -> str:
        return " ".join(
            filter(
                None,
                [
                    row.work_order_code,
                    row.title,
                    row.description,
                    row.failure_code,
                    row.root_cause_code,
                    row.work_order_type.value,
                    row.status.value,
                ],
            )
        ).lower()

    @staticmethod
    def _format_window(started_at, ended_at) -> str:
        if started_at is None and ended_at is None:
            return "-"
        return f"{format_timestamp(started_at)} -> {format_timestamp(ended_at)}"

    def _on_site_changed(self) -> None:
        self.reload_data()

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

    def _on_domain_change(self, event: DomainChangeEvent) -> None:
        if getattr(event, "scope_code", "") == "maintenance_management":
            self.reload_planning_data()

    def _on_modules_changed(self, _module_code: str) -> None:
        self.reload_planning_data()

    def _on_organization_changed(self, _organization_id: str) -> None:
        self.reload_data()

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenancePlannerTab"]
