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
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenanceIntegrationSourceService,
    MaintenanceLocationService,
    MaintenanceSensorExceptionService,
    MaintenanceSensorReadingService,
    MaintenanceSensorService,
    MaintenanceSensorSourceMappingService,
    MaintenanceSystemService,
)
from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org import SiteService
from ui.modules.maintenance_management.sensors.dialogs import MaintenanceSensorDetailDialog
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
from src.ui.shared.widgets.guards import make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class MaintenanceSensorsTab(QWidget):
    def __init__(
        self,
        *,
        sensor_service: MaintenanceSensorService,
        sensor_reading_service: MaintenanceSensorReadingService,
        sensor_source_mapping_service: MaintenanceSensorSourceMappingService,
        sensor_exception_service: MaintenanceSensorExceptionService,
        integration_source_service: MaintenanceIntegrationSourceService,
        site_service: SiteService,
        asset_service: MaintenanceAssetService,
        component_service: MaintenanceAssetComponentService,
        location_service: MaintenanceLocationService,
        system_service: MaintenanceSystemService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sensor_service = sensor_service
        self._sensor_reading_service = sensor_reading_service
        self._sensor_source_mapping_service = sensor_source_mapping_service
        self._sensor_exception_service = sensor_exception_service
        self._integration_source_service = integration_source_service
        self._site_service = site_service
        self._asset_service = asset_service
        self._component_service = component_service
        self._location_service = location_service
        self._system_service = system_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._site_labels: dict[str, str] = {}
        self._asset_labels: dict[str, str] = {}
        self._component_labels: dict[str, str] = {}
        self._system_labels: dict[str, str] = {}
        self._sensor_rows = []
        self._integration_rows = []
        self._exception_rows = []
        self._sensor_detail_dialog: MaintenanceSensorDetailDialog | None = None
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
        self.sensor_count_badge = make_meta_badge("0 sensors")
        self.exception_badge = make_meta_badge("0 open exceptions")
        build_maintenance_header(
            root=root,
            object_name="maintenanceSensorsHeaderCard",
            eyebrow_text="SENSORS AND INTEGRATIONS",
            title_text="Sensors",
            subtitle_text="Monitor sensor health, incoming integration status, and exception queues from one maintenance workbench.",
            badges=(self.context_badge, self.sensor_count_badge, self.exception_badge),
        )

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceSensorsControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel(
            "Filters: All sites | All assets | All systems | Active only | All qualities | All sensor types"
        )
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
        self.active_combo = QComboBox()
        self.quality_combo = QComboBox()
        self.sensor_type_combo = QComboBox()
        self.source_type_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, name, tag, source, unit, or anchor")
        self.active_combo.addItem("Active only", True)
        self.active_combo.addItem("Inactive only", False)
        self.active_combo.addItem("All statuses", None)
        self.quality_combo.addItem("All qualities", None)
        self.quality_combo.addItem("Valid", "VALID")
        self.quality_combo.addItem("Stale", "STALE")
        self.quality_combo.addItem("Error", "ERROR")
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Asset"), 0, 2)
        filter_row.addWidget(self.asset_combo, 0, 3)
        filter_row.addWidget(QLabel("System"), 1, 0)
        filter_row.addWidget(self.system_combo, 1, 1)
        filter_row.addWidget(QLabel("Lifecycle"), 1, 2)
        filter_row.addWidget(self.active_combo, 1, 3)
        filter_row.addWidget(QLabel("Quality"), 2, 0)
        filter_row.addWidget(self.quality_combo, 2, 1)
        filter_row.addWidget(QLabel("Sensor type"), 2, 2)
        filter_row.addWidget(self.sensor_type_combo, 2, 3)
        filter_row.addWidget(QLabel("Source type"), 3, 0)
        filter_row.addWidget(self.source_type_combo, 3, 1)
        filter_row.addWidget(QLabel("Search"), 3, 2)
        filter_row.addWidget(self.search_edit, 3, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_sensors_card = KpiCard("Sensors", "-", "Visible in current scope", CFG.COLOR_ACCENT)
        self.attention_card = KpiCard("Attention", "-", "Stale or error quality", CFG.COLOR_WARNING)
        self.integration_card = KpiCard("Integrations", "-", "Tracked source connections", CFG.COLOR_SUCCESS)
        self.open_exceptions_card = KpiCard("Open Exceptions", "-", "Planner review queue", CFG.COLOR_ACCENT)
        for card in (
            self.total_sensors_card,
            self.attention_card,
            self.integration_card,
            self.open_exceptions_card,
        ):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        self.workbench = MaintenanceWorkbenchNavigator(object_name="maintenanceSensorsWorkbench", parent=self)
        self.sensor_panel = self._build_sensor_panel()
        self.integration_panel = self._build_integration_panel()
        self.exception_panel = self._build_exception_panel()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(
                    key="sensor_register",
                    label="Sensor Register",
                    widget=self.sensor_panel,
                ),
                MaintenanceWorkbenchSection(
                    key="integration_queue",
                    label="Integration Queue",
                    widget=self.integration_panel,
                ),
                MaintenanceWorkbenchSection(
                    key="exception_queue",
                    label="Exception Queue",
                    widget=self.exception_panel,
                ),
            ],
            initial_key="sensor_register",
        )
        root.addWidget(self.workbench, 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.asset_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self.reload_sensors)
        )
        self.system_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self.reload_sensors)
        )
        self.active_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self.reload_sensors)
        )
        self.quality_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self.reload_sensors)
        )
        self.sensor_type_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self.reload_sensors)
        )
        self.source_type_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self.reload_sensors)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self.reload_sensors)
        )
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self.reload_data)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.sensor_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self._on_sensor_selection_changed)
        )
        self.btn_view_sensor_detail.clicked.connect(
            make_guarded_slot(self, title="Maintenance Sensors", callback=self._open_sensor_detail_dialog)
        )

    def _build_sensor_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceSensorsGridSurface",
            alt=False,
        )
        #title = QLabel("Sensor Register")
        #title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Maintenance sensors, counters, and condition points active in the current scope.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        #layout.addWidget(title)
        layout.addWidget(subtitle)
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.sensor_selection_summary = QLabel("Select a sensor, then open its detail workbench.")
        self.sensor_selection_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.sensor_selection_summary.setWordWrap(True)
        action_row.addWidget(self.sensor_selection_summary, 1)
        self.btn_view_sensor_detail = QPushButton("View Sensor Detail")
        self.btn_view_sensor_detail.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_view_sensor_detail.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_view_sensor_detail)
        layout.addLayout(action_row)
        self.sensor_table = build_admin_table(
            headers=("Sensor", "Anchor", "Type", "Source", "Quality", "Last Read"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.sensor_table)
        return panel

    def _build_integration_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceIntegrationStatusSurface",
            alt=False,
        )
        #title = QLabel("Integration Queue")
        #title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Connectivity and sync health for maintenance sensor source integrations.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        #layout.addWidget(title)
        layout.addWidget(subtitle)
        self.integration_table = build_admin_table(
            headers=("Integration", "Type", "Status", "Last Success", "Last Failure"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.integration_table)
        return panel

    def _build_exception_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceSensorExceptionSurface",
            alt=False,
        )
        #title = QLabel("Exception Queue")
        #title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Sensor and sync exceptions that need planner or reliability review.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        #layout.addWidget(title)
        layout.addWidget(subtitle)
        self.exception_table = build_admin_table(
            headers=("Exception", "Anchor", "Status", "Detected", "Batch"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._stretch(),
            ),
        )
        layout.addWidget(self.exception_table)
        return panel

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_asset_id = selected_combo_value(self.asset_combo)
        selected_system_id = selected_combo_value(self.system_combo)
        selected_sensor_type = selected_combo_value(self.sensor_type_combo)
        selected_source_type = selected_combo_value(self.source_type_combo)
        selected_sensor_id = self._selected_sensor_id()
        try:
            sites = self._site_service.list_sites(active_only=None)
            assets = self._asset_service.list_assets(active_only=None, site_id=selected_site_id)
            systems = self._system_service.list_systems(active_only=None, site_id=selected_site_id)
            components = []
            for asset in assets:
                components.extend(self._component_service.list_components(active_only=None, asset_id=asset.id))
            sensor_catalog = self._sensor_service.list_sensors(
                active_only=None,
                site_id=selected_site_id,
                asset_id=selected_asset_id,
                system_id=selected_system_id,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Sensors", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Sensors", f"Failed to load maintenance sensor filters: {exc}")
            return

        self._site_labels = {row.id: row.name for row in sites}
        self._asset_labels = {row.id: f"{row.asset_code} - {row.name}" for row in assets}
        self._component_labels = {row.id: f"{row.component_code} - {row.name}" for row in components}
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
        sensor_types = sorted({row.sensor_type for row in sensor_catalog if row.sensor_type})
        source_types = sorted({row.source_type for row in sensor_catalog if row.source_type})
        reset_combo_options(
            self.sensor_type_combo,
            placeholder="All sensor types",
            options=[(row.replace("_", " ").title(), row) for row in sensor_types],
            selected_value=selected_sensor_type,
        )
        reset_combo_options(
            self.source_type_combo,
            placeholder="All source types",
            options=[(row.replace("_", " ").title(), row) for row in source_types],
            selected_value=selected_source_type,
        )
        self.reload_sensors(selected_sensor_id=selected_sensor_id)

    def reload_sensors(self, *, selected_sensor_id: str | None = None) -> None:
        selected_sensor_id = selected_sensor_id or self._selected_sensor_id()
        try:
            self._sensor_rows = self._sensor_service.search_sensors(
                search_text=self.search_edit.text(),
                active_only=self.active_combo.currentData(),
                site_id=selected_combo_value(self.site_combo),
                asset_id=selected_combo_value(self.asset_combo),
                system_id=selected_combo_value(self.system_combo),
                sensor_type=selected_combo_value(self.sensor_type_combo),
                source_type=selected_combo_value(self.source_type_combo),
            )
            quality_filter = selected_combo_value(self.quality_combo)
            if quality_filter:
                self._sensor_rows = [
                    row for row in self._sensor_rows if row.last_quality_state.value == quality_filter
                ]
            try:
                self._integration_rows = self._integration_source_service.list_sources(active_only=None)
            except BusinessRuleError:
                self._integration_rows = []
            try:
                self._exception_rows = self._sensor_exception_service.list_exceptions()
            except BusinessRuleError:
                self._exception_rows = []
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Sensors", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Sensors", f"Failed to load maintenance sensors: {exc}")
            return

        visible_sensor_ids = {row.id for row in self._sensor_rows}
        visible_source_ids = {row.id for row in self._integration_rows}
        filtered_exceptions = [
            row
            for row in self._exception_rows
            if (
                (row.sensor_id and row.sensor_id in visible_sensor_ids)
                or (row.integration_source_id and row.integration_source_id in visible_source_ids)
            )
        ]
        attention_count = sum(
            1 for row in self._sensor_rows if row.last_quality_state.value in {"STALE", "ERROR"}
        )
        open_exception_count = sum(1 for row in filtered_exceptions if row.status.value == "OPEN")

        self.total_sensors_card.set_value(str(len(self._sensor_rows)))
        self.attention_card.set_value(str(attention_count))
        self.integration_card.set_value(str(len(self._integration_rows)))
        self.open_exceptions_card.set_value(str(open_exception_count))
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.sensor_count_badge.setText(f"{len(self._sensor_rows)} sensors")
        self.exception_badge.setText(f"{open_exception_count} open exceptions")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.asset_combo.currentText()} | {self.system_combo.currentText()} | "
            f"{self.active_combo.currentText()} | {self.quality_combo.currentText()} | {self.sensor_type_combo.currentText()} | {self.source_type_combo.currentText()}"
            + (
                f" | Search: {self.search_edit.text().strip()}"
                if self.search_edit.text().strip()
                else ""
            )
        )
        self._populate_sensor_table(selected_sensor_id=selected_sensor_id)
        self._populate_integration_table()
        self._populate_exception_table(filtered_exceptions)
        self._sync_sensor_actions()

    def _populate_sensor_table(self, *, selected_sensor_id: str | None) -> None:
        self.sensor_table.blockSignals(True)
        self.sensor_table.setRowCount(len(self._sensor_rows))
        selected_row = 0 if self._sensor_rows else -1
        for row_index, row in enumerate(self._sensor_rows):
            values = (
                f"{row.sensor_code} - {row.sensor_name}",
                self._anchor_label(row),
                row.sensor_type.replace("_", " ").title() or "-",
                row.source_name or row.source_type.replace("_", " ").title() or "-",
                row.last_quality_state.value.title(),
                format_timestamp(row.last_read_at),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.sensor_table.setItem(row_index, column, item)
            if selected_sensor_id and row.id == selected_sensor_id:
                selected_row = row_index
        self.sensor_table.blockSignals(False)
        if selected_row >= 0:
            self.sensor_table.selectRow(selected_row)
            return
        self.sensor_table.clearSelection()

    def _populate_integration_table(self) -> None:
        self.integration_table.setRowCount(len(self._integration_rows))
        for row_index, row in enumerate(self._integration_rows):
            values = (
                f"{row.integration_code} - {row.name}",
                row.integration_type.replace("_", " ").title(),
                self._integration_status_label(row),
                format_timestamp(row.last_successful_sync_at),
                format_timestamp(row.last_failed_sync_at),
            )
            for column, value in enumerate(values):
                self.integration_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_exception_table(self, rows) -> None:
        self.exception_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row.exception_type.value.replace("_", " ").title(),
                self._exception_anchor_label(row),
                row.status.value.title(),
                format_timestamp(row.detected_at),
                row.source_batch_id or "-",
            )
            for column, value in enumerate(values):
                self.exception_table.setItem(row_index, column, QTableWidgetItem(value))

    def _selected_sensor_id(self) -> str | None:
        row = self.sensor_table.currentRow()
        if row < 0:
            return None
        item = self.sensor_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_sensor(self):
        sensor_id = self._selected_sensor_id()
        if not sensor_id:
            return None
        return next((row for row in self._sensor_rows if row.id == sensor_id), None)

    def _sync_sensor_actions(self) -> None:
        sensor = self._selected_sensor()
        if sensor is None:
            self.sensor_selection_summary.setText("Select a sensor, then open its detail workbench.")
            self.btn_view_sensor_detail.setEnabled(False)
            return
        self.sensor_selection_summary.setText(
            f"Selected: {sensor.sensor_code} | Quality: {sensor.last_quality_state.value.title()} | Last read: {format_timestamp(sensor.last_read_at)}"
        )
        self.btn_view_sensor_detail.setEnabled(True)

    def _open_sensor_detail_dialog(self) -> None:
        sensor_id = self._selected_sensor_id()
        if not sensor_id:
            QMessageBox.information(self, "Maintenance Sensors", "Select a sensor to open its detail workbench.")
            return
        dialog = MaintenanceSensorDetailDialog(
            sensor_service=self._sensor_service,
            sensor_reading_service=self._sensor_reading_service,
            sensor_source_mapping_service=self._sensor_source_mapping_service,
            integration_source_service=self._integration_source_service,
            site_labels=self._site_labels,
            asset_labels=self._asset_labels,
            component_labels=self._component_labels,
            system_labels=self._system_labels,
            parent=self,
        )
        dialog.load_sensor(sensor_id)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._sensor_detail_dialog = dialog

    def _anchor_label(self, sensor) -> str:
        if sensor.component_id:
            return self._component_labels.get(sensor.component_id, sensor.component_id)
        if sensor.asset_id:
            return self._asset_labels.get(sensor.asset_id, sensor.asset_id)
        if sensor.system_id:
            return self._system_labels.get(sensor.system_id, sensor.system_id)
        return self._site_labels.get(sensor.site_id, sensor.site_id)

    def _exception_anchor_label(self, exception) -> str:
        if exception.sensor_id:
            sensor = next((row for row in self._sensor_rows if row.id == exception.sensor_id), None)
            if sensor is not None:
                return self._anchor_label(sensor)
        if exception.integration_source_id:
            source = next((row for row in self._integration_rows if row.id == exception.integration_source_id), None)
            if source is not None:
                return f"{source.integration_code} - {source.name}"
        return "-"

    @staticmethod
    def _integration_status_label(source) -> str:
        if not source.is_active:
            return "Inactive"
        if source.last_failed_sync_at and (
            source.last_successful_sync_at is None or source.last_failed_sync_at >= source.last_successful_sync_at
        ):
            return "Attention"
        if source.last_successful_sync_at is not None:
            return "Healthy"
        return "Pending"

    def _on_site_changed(self) -> None:
        self.reload_data()

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

    def _on_sensor_selection_changed(self) -> None:
        self._sync_sensor_actions()

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


__all__ = ["MaintenanceSensorsTab"]
