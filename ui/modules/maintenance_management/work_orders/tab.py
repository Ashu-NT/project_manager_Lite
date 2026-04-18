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

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenanceDocumentService,
    MaintenanceLaborService,
    MaintenanceLocationService,
    MaintenanceSystemService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderService,
    MaintenanceWorkOrderTaskService,
    MaintenanceWorkOrderTaskStepService,
    MaintenanceWorkRequestService,
)
from core.modules.maintenance_management.domain import (
    MaintenancePriority,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderType,
)
from src.core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org import SiteService
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
from ui.modules.maintenance_management.work_orders.dialogs import MaintenanceWorkOrderDetailDialog
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.modules.project_management.dashboard.widgets import KpiCard
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
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


class MaintenanceWorkOrdersTab(QWidget):
    def __init__(
        self,
        *,
        work_order_service: MaintenanceWorkOrderService,
        work_order_task_service: MaintenanceWorkOrderTaskService,
        work_order_task_step_service: MaintenanceWorkOrderTaskStepService,
        material_requirement_service: MaintenanceWorkOrderMaterialRequirementService,
        labor_service: MaintenanceLaborService | None = None,
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
        self._labor_service = labor_service
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
        self._detail_dialog: MaintenanceWorkOrderDetailDialog | None = None
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
            subtitle_text="Run the corrective and preventive queue, then open focused work-order detail popups for tasks, steps, materials, and evidence.",
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

        root.addWidget(self._build_queue_panel(), 1)

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
        self.btn_open_detail.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Orders", callback=self._open_detail_dialog)
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
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.selection_summary = QLabel(
            "Select a work order, then click Open Detail to open its separate execution workbench."
        )
        self.selection_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.selection_summary.setWordWrap(True)
        action_row.addWidget(self.selection_summary, 1)
        self.btn_open_detail = QPushButton("Open Detail")
        self.btn_open_detail.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_open_detail.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_open_detail)
        layout.addLayout(action_row)
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

    def reload_work_orders(self, *, selected_work_order_id: str | None = None) -> None:
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
            rows: list[MaintenanceWorkOrder] = [row for row in rows if row.assigned_employee_id]
        elif responsibility_filter == _RESPONSIBILITY_TEAM:
            rows: list[MaintenanceWorkOrder] = [row for row in rows if row.assigned_team_id]
        elif responsibility_filter == _RESPONSIBILITY_UNASSIGNED:
            rows: list[MaintenanceWorkOrder] = [row for row in rows if not row.assigned_employee_id and not row.assigned_team_id]

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
        self._populate_work_order_table(rows, selected_work_order_id=selected_work_order_id)

    def _populate_work_order_table(self, rows: list[MaintenanceWorkOrder], *, selected_work_order_id: str | None) -> None:
        self.work_order_table.blockSignals(True)
        self.work_order_table.setRowCount(len(rows))
        selected_row = -1
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
        else:
            self.work_order_table.clearSelection()
        self.work_order_table.blockSignals(False)
        self._sync_selection_actions()

    def _selected_work_order_id(self) -> str | None:
        row = self.work_order_table.currentRow()
        if row < 0:
            return None
        item = self.work_order_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_work_order(self):
        work_order_id = self._selected_work_order_id()
        if not work_order_id:
            return None
        try:
            return self._work_order_service.get_work_order(work_order_id)
        except Exception:  # noqa: BLE001
            return None

    def _sync_selection_actions(self) -> None:
        work_order = self._selected_work_order()
        if work_order is None:
            self.selection_summary.setText(
                "Select a work order, then click Open Detail to open its separate execution workbench."
            )
            self.btn_open_detail.setEnabled(False)
            return
        self.selection_summary.setText(
            f"Selected: {work_order.work_order_code} | Status: {work_order.status.value.replace('_', ' ').title()} | Priority: {work_order.priority.value.title()}"
        )
        self.btn_open_detail.setEnabled(True)

    def _open_detail_dialog(self) -> None:
        work_order_id = self._selected_work_order_id()
        if not work_order_id:
            QMessageBox.information(self, "Maintenance Work Orders", "Select a work order to open its detail popup.")
            return
        dialog = MaintenanceWorkOrderDetailDialog(
            work_order_service=self._work_order_service,
            work_order_task_service=self._work_order_task_service,
            work_order_task_step_service=self._work_order_task_step_service,
            material_requirement_service=self._material_requirement_service,
            labor_service=self._labor_service,
            document_service=self._document_service,
            work_request_service=self._work_request_service,
            site_labels=self._site_labels,
            asset_labels=self._asset_labels,
            location_labels=self._location_labels,
            system_labels=self._system_labels,
            parent=self,
        )
        dialog.load_work_order(work_order_id)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._detail_dialog = dialog

    def _on_work_order_selection_changed(self) -> None:
        self._sync_selection_actions()

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
    def _format_plan_window(work_order) -> str:
        if work_order.planned_start is None and work_order.planned_end is None:
            return "-"
        if work_order.planned_start is None:
            return f"Until {format_timestamp(work_order.planned_end)}"
        if work_order.planned_end is None:
            return f"From {format_timestamp(work_order.planned_start)}"
        return f"{format_timestamp(work_order.planned_start)} -> {format_timestamp(work_order.planned_end)}"

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceWorkOrdersTab"]
