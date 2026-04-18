from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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
    MaintenanceLocationService,
    MaintenanceSystemService,
    MaintenanceWorkOrderService,
    MaintenanceWorkRequestService,
)
from core.modules.maintenance_management.domain import MaintenancePriority, MaintenanceWorkRequestStatus
from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org import SiteService
from ui.modules.maintenance_management.requests.edit_dialogs import (
    MaintenanceRequestConvertDialog,
    MaintenanceRequestEditDialog,
)
from ui.modules.maintenance_management.requests.dialogs import MaintenanceRequestDetailDialog
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
from src.ui.platform.widgets.admin_surface import build_admin_surface_card, build_admin_table
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class MaintenanceRequestsTab(QWidget):
    def __init__(
        self,
        *,
        work_request_service: MaintenanceWorkRequestService,
        work_order_service: MaintenanceWorkOrderService,
        site_service: SiteService,
        asset_service: MaintenanceAssetService,
        location_service: MaintenanceLocationService,
        system_service: MaintenanceSystemService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._work_request_service = work_request_service
        self._work_order_service = work_order_service
        self._site_service = site_service
        self._asset_service = asset_service
        self._location_service = location_service
        self._system_service = system_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(user_session, "maintenance.manage")
        self._site_labels: dict[str, str] = {}
        self._asset_labels: dict[str, str] = {}
        self._location_labels: dict[str, str] = {}
        self._system_labels: dict[str, str] = {}
        self._detail_dialog: MaintenanceRequestDetailDialog | None = None
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
        self.queue_badge = make_meta_badge("0 requests")
        self.status_badge = make_meta_badge("Queue status mix")
        build_maintenance_header(
            root=root,
            object_name="maintenanceRequestsHeaderCard",
            eyebrow_text="REQUEST INTAKE",
            title_text="Requests",
            subtitle_text="Triage incoming maintenance demand, inspect asset context, and follow linked work-order conversion from one queue.",
            badges=(self.context_badge, self.queue_badge, self.status_badge),
        )

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceRequestsControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All statuses | All priorities")
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
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, title, type, requester, risk, or symptom")
        self.status_combo.addItem("All statuses", None)
        for status in MaintenanceWorkRequestStatus:
            self.status_combo.addItem(status.value.title(), status.value)
        self.priority_combo.addItem("All priorities", None)
        for priority in MaintenancePriority:
            self.priority_combo.addItem(priority.value.title(), priority.value)
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Status"), 0, 2)
        filter_row.addWidget(self.status_combo, 0, 3)
        filter_row.addWidget(QLabel("Priority"), 1, 0)
        filter_row.addWidget(self.priority_combo, 1, 1)
        filter_row.addWidget(QLabel("Search"), 1, 2)
        filter_row.addWidget(self.search_edit, 1, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Requests", "-", "Visible in current queue", CFG.COLOR_ACCENT)
        self.new_card = KpiCard("New", "-", "Waiting first triage", CFG.COLOR_WARNING)
        self.triaged_card = KpiCard("Triaged", "-", "Reviewed and staged", CFG.COLOR_SUCCESS)
        self.deferred_card = KpiCard("Deferred", "-", "Held for later action", CFG.COLOR_ACCENT)
        for card in (self.total_card, self.new_card, self.triaged_card, self.deferred_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        root.addWidget(self._build_queue_panel(), 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Requests", callback=self.reload_requests)
        )
        self.priority_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Requests", callback=self.reload_requests)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Maintenance Requests", callback=self.reload_requests)
        )
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Requests", callback=self.reload_data)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.request_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Requests", callback=self._on_request_selection_changed)
        )
        self.btn_new_request.clicked.connect(
            make_guarded_slot(self, title="Maintenance Requests", callback=self._open_new_request_dialog)
        )
        self.btn_convert_request.clicked.connect(
            make_guarded_slot(self, title="Maintenance Requests", callback=self._convert_selected_request)
        )
        self.btn_open_detail.clicked.connect(
            make_guarded_slot(self, title="Maintenance Requests", callback=self._open_detail_dialog)
        )
        apply_permission_hint(self.btn_new_request, allowed=self._can_manage, missing_permission="maintenance.manage")
        apply_permission_hint(
            self.btn_convert_request,
            allowed=self._can_manage,
            missing_permission="maintenance.manage",
        )

    def _build_queue_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceRequestQueueSurface",
            alt=False,
        )
        title = QLabel("Request Queue")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Incoming corrective and operational demand for maintenance planners and supervisors.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.selection_summary = QLabel(
            "Select a request, then click Open Detail to inspect intake, impact, and linked work orders."
        )
        self.selection_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.selection_summary.setWordWrap(True)
        action_row.addWidget(self.selection_summary, 1)
        self.btn_new_request = QPushButton("New Request")
        self.btn_new_request.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_new_request.setStyleSheet(dashboard_action_button_style("primary"))
        action_row.addWidget(self.btn_new_request)
        self.btn_convert_request = QPushButton("Convert to Work Order")
        self.btn_convert_request.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_convert_request.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_convert_request)
        self.btn_open_detail = QPushButton("Open Detail")
        self.btn_open_detail.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_open_detail.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_open_detail)
        layout.addLayout(action_row)
        self.request_table = build_admin_table(
            headers=("Request", "Type", "Status", "Priority", "Requested By", "Requested"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.request_table)
        return panel

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_request_id = self._selected_request_id()
        try:
            sites = self._site_service.list_sites(active_only=None)
            assets = self._asset_service.list_assets(active_only=None, site_id=selected_site_id)
            systems = self._system_service.list_systems(active_only=None, site_id=selected_site_id)
            locations = self._location_service.list_locations(active_only=None, site_id=selected_site_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Requests", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Requests", f"Failed to load request filters: {exc}")
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
        self.reload_requests(selected_request_id=selected_request_id)

    def reload_requests(self, *, selected_request_id: str | None = None) -> None:
        selected_request_id = selected_request_id or self._selected_request_id()
        try:
            rows = self._work_request_service.search_work_requests(
                search_text=self.search_edit.text(),
                site_id=selected_combo_value(self.site_combo),
                status=selected_combo_value(self.status_combo),
                priority=selected_combo_value(self.priority_combo),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Requests", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Requests", f"Failed to load maintenance requests: {exc}")
            return

        self.total_card.set_value(str(len(rows)))
        self.new_card.set_value(str(sum(1 for row in rows if row.status == MaintenanceWorkRequestStatus.NEW)))
        self.triaged_card.set_value(str(sum(1 for row in rows if row.status == MaintenanceWorkRequestStatus.TRIAGED)))
        self.deferred_card.set_value(str(sum(1 for row in rows if row.status == MaintenanceWorkRequestStatus.DEFERRED)))
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.queue_badge.setText(f"{len(rows)} requests")
        self.status_badge.setText(
            f"{sum(1 for row in rows if row.status == MaintenanceWorkRequestStatus.CONVERTED)} converted"
        )
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.status_combo.currentText()} | {self.priority_combo.currentText()}"
            + (
                f" | Search: {self.search_edit.text().strip()}"
                if self.search_edit.text().strip()
                else ""
            )
        )
        self._populate_request_table(rows, selected_request_id=selected_request_id)

    def _populate_request_table(self, rows, *, selected_request_id: str | None) -> None:
        self.request_table.blockSignals(True)
        self.request_table.setRowCount(len(rows))
        selected_row = -1
        for row_index, request in enumerate(rows):
            values = (
                f"{request.work_request_code} - {request.title or request.request_type.title()}",
                request.request_type.title(),
                request.status.value.title(),
                request.priority.value.title(),
                request.requested_by_name_snapshot or "-",
                format_timestamp(request.requested_at),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, request.id)
                self.request_table.setItem(row_index, column, item)
            if selected_request_id and request.id == selected_request_id:
                selected_row = row_index
        self.request_table.blockSignals(False)
        if selected_row >= 0:
            self.request_table.selectRow(selected_row)
            self._sync_selection_actions()
            return
        self.request_table.clearSelection()
        self._sync_selection_actions()

    def _on_site_changed(self) -> None:
        self.reload_data()

    def _on_request_selection_changed(self) -> None:
        self._sync_selection_actions()

    def _selected_request(self):
        request_id = self._selected_request_id()
        if not request_id:
            return None
        try:
            return self._work_request_service.get_work_request(request_id)
        except Exception:  # noqa: BLE001
            return None

    def _sync_selection_actions(self) -> None:
        request = self._selected_request()
        if request is None:
            self.selection_summary.setText(
                "Select a request, then click Open Detail to inspect intake, impact, and linked work orders."
            )
            self.btn_new_request.setEnabled(self._can_manage)
            self.btn_convert_request.setEnabled(False)
            self.btn_open_detail.setEnabled(False)
            return
        linked_orders = self._linked_orders_for_request(request)
        self.selection_summary.setText(
            f"Selected: {request.work_request_code} | Status: {request.status.value.title()} | "
            f"Priority: {request.priority.value.title()} | Linked orders: {len(linked_orders)}"
        )
        self.btn_new_request.setEnabled(self._can_manage)
        self.btn_convert_request.setEnabled(self._can_manage and self._can_convert_request(request, linked_orders))
        self.btn_open_detail.setEnabled(True)

    def _open_detail_dialog(self) -> None:
        request_id = self._selected_request_id()
        if not request_id:
            QMessageBox.information(self, "Maintenance Requests", "Select a request to open its detail view.")
            return
        dialog = MaintenanceRequestDetailDialog(
            work_request_service=self._work_request_service,
            work_order_service=self._work_order_service,
            site_labels=self._site_labels,
            asset_labels=self._asset_labels,
            location_labels=self._location_labels,
            system_labels=self._system_labels,
            parent=self,
        )
        dialog.load_request(request_id)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._detail_dialog = dialog

    def _open_new_request_dialog(self) -> None:
        if not self._can_manage:
            QMessageBox.information(self, "Maintenance Requests", "You do not have permission to create maintenance requests.")
            return
        selected_site_id = selected_combo_value(self.site_combo)
        try:
            sites = self._site_service.list_sites(active_only=None)
            assets = self._asset_service.list_assets(active_only=None, site_id=selected_site_id)
            systems = self._system_service.list_systems(active_only=None, site_id=selected_site_id)
            locations = self._location_service.list_locations(active_only=None, site_id=selected_site_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Requests", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Requests", f"Failed to load request intake options: {exc}")
            return
        dialog = MaintenanceRequestEditDialog(
            site_options=[(f"{site.site_code} - {site.name}", site.id) for site in sites],
            asset_options=[(f"{asset.asset_code} - {asset.name}", asset.id) for asset in assets],
            system_options=[(f"{system.system_code} - {system.name}", system.id) for system in systems],
            location_options=[(f"{location.location_code} - {location.name}", location.id) for location in locations],
            selected_site_id=selected_site_id,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._work_request_service.create_work_request(
                site_id=dialog.site_id,
                work_request_code=dialog.request_code,
                source_type=dialog.source_type,
                request_type=dialog.request_type,
                asset_id=dialog.asset_id,
                system_id=dialog.system_id,
                location_id=dialog.location_id,
                title=dialog.title,
                description=dialog.description,
                priority=dialog.priority,
                failure_symptom_code=dialog.failure_symptom_code,
                safety_risk_level=dialog.safety_risk_level,
                production_impact_level=dialog.production_impact_level,
                notes=dialog.notes,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Requests", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Requests", f"Failed to create maintenance request: {exc}")
            return
        self.reload_data()

    def _convert_selected_request(self) -> None:
        request = self._selected_request()
        if request is None:
            QMessageBox.information(self, "Maintenance Requests", "Select a request to convert into a work order.")
            return
        linked_orders = self._linked_orders_for_request(request)
        if not self._can_convert_request(request, linked_orders):
            QMessageBox.information(
                self,
                "Maintenance Requests",
                "This request is not currently eligible for conversion into a new work order.",
            )
            return
        dialog = MaintenanceRequestConvertDialog(work_request=request, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._work_order_service.create_work_order(
                site_id=request.site_id,
                work_order_code=dialog.work_order_code,
                work_order_type=dialog.work_order_type,
                source_type="work_request",
                source_id=request.id,
                title=dialog.title,
                description=dialog.description,
                assigned_team_id=dialog.assigned_team_id,
                requires_shutdown=dialog.requires_shutdown,
                permit_required=dialog.permit_required,
                approval_required=dialog.approval_required,
                notes=dialog.notes,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Requests", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Requests", f"Failed to convert request into work order: {exc}")
            return
        self.reload_data()

    def _linked_orders_for_request(self, request):
        return [
            row
            for row in self._work_order_service.list_work_orders(site_id=request.site_id)
            if row.source_type == "WORK_REQUEST" and row.source_id == request.id
        ]

    @staticmethod
    def _can_convert_request(request, linked_orders) -> bool:
        if request.status.value in {"REJECTED", "CONVERTED"}:
            return False
        return len(linked_orders) == 0

    def _selected_request_id(self) -> str | None:
        row = self.request_table.currentRow()
        if row < 0:
            return None
        item = self.request_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

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
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceRequestsTab"]
