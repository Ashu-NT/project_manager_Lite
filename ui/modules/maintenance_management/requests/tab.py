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
    MaintenanceLocationService,
    MaintenanceSystemService,
    MaintenanceWorkOrderService,
    MaintenanceWorkRequestService,
)
from core.modules.maintenance_management.domain import MaintenancePriority, MaintenanceWorkRequestStatus
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
from ui.platform.shared.guards import make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


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
        self._site_labels: dict[str, str] = {}
        self._asset_labels: dict[str, str] = {}
        self._location_labels: dict[str, str] = {}
        self._system_labels: dict[str, str] = {}
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

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)
        content_row.addWidget(self._build_queue_panel(), 3)
        content_row.addWidget(self._build_detail_panel(), 2)
        root.addLayout(content_row, 1)

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

    def _build_detail_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceRequestDetailSurface",
            alt=False,
        )
        title = QLabel("Selected Request")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Request context, operational impact, and linked work-order conversion.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.detail_title = QLabel("No request selected")
        self.detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        layout.addWidget(self.detail_title)
        self.detail_summary = QLabel("Select a request to inspect maintenance intake context and follow-on work.")
        self.detail_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.detail_summary.setWordWrap(True)
        layout.addWidget(self.detail_summary)
        related_title = QLabel("Linked Work Orders")
        related_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(related_title)
        self.linked_orders_table = build_admin_table(
            headers=("Work Order", "Status", "Priority", "Type"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.linked_orders_table)
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
        selected_row = 0 if rows else -1
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
            self._refresh_request_details(rows[selected_row].id)
            return
        self._clear_request_details()

    def _on_site_changed(self) -> None:
        self.reload_data()

    def _on_request_selection_changed(self) -> None:
        request_id = self._selected_request_id()
        if request_id:
            self._refresh_request_details(request_id)
            return
        self._clear_request_details()

    def _refresh_request_details(self, request_id: str) -> None:
        try:
            request = self._work_request_service.get_work_request(request_id)
            related_orders = [
                row
                for row in self._work_order_service.list_work_orders(site_id=request.site_id)
                if row.source_type == "WORK_REQUEST" and row.source_id == request.id
            ]
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Requests", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Requests", f"Failed to load request details: {exc}")
            return

        self.detail_title.setText(f"{request.work_request_code} - {request.title or request.request_type.title()}")
        self.detail_summary.setText(
            "\n".join(
                [
                    f"Type: {request.request_type.title()} | Status: {request.status.value.title()} | Priority: {request.priority.value.title()}",
                    f"Site: {self._site_labels.get(request.site_id, request.site_id)}",
                    f"Asset: {self._label_for(self._asset_labels, request.asset_id)} | System: {self._label_for(self._system_labels, request.system_id)}",
                    f"Location: {self._label_for(self._location_labels, request.location_id)} | Component: {request.component_id or '-'}",
                    f"Failure symptom: {request.failure_symptom_code or '-'}",
                    f"Safety risk: {request.safety_risk_level or '-'} | Production impact: {request.production_impact_level or '-'}",
                    f"Requested by: {request.requested_by_name_snapshot or '-'} | Triaged: {format_timestamp(request.triaged_at)}",
                    f"Description: {request.description or '-'}",
                    f"Notes: {request.notes or '-'}",
                ]
            )
        )
        self.linked_orders_table.setRowCount(len(related_orders))
        for row_index, order in enumerate(related_orders):
            values = (
                f"{order.work_order_code} - {order.title or order.work_order_type.value.title()}",
                order.status.value.title(),
                order.priority.value.title(),
                order.work_order_type.value.title(),
            )
            for column, value in enumerate(values):
                self.linked_orders_table.setItem(row_index, column, QTableWidgetItem(value))

    def _clear_request_details(self) -> None:
        self.detail_title.setText("No request selected")
        self.detail_summary.setText("Select a request to inspect maintenance intake context and follow-on work.")
        self.linked_orders_table.setRowCount(0)

    def _selected_request_id(self) -> str | None:
        row = self.request_table.currentRow()
        if row < 0:
            return None
        item = self.request_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    @staticmethod
    def _label_for(labels: dict[str, str], value: str | None) -> str:
        if not value:
            return "-"
        return labels.get(value, value)

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
