from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidgetItem, QVBoxLayout, QWidget, QDialog

from core.modules.maintenance_management import (
    MaintenanceIntegrationSourceService,
    MaintenanceSensorReadingService,
    MaintenanceSensorService,
    MaintenanceSensorSourceMappingService,
)
from ui.modules.maintenance_management.shared import (
    MaintenanceWorkbenchNavigator,
    MaintenanceWorkbenchSection,
    format_timestamp,
)
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceSensorDetailDialog(QDialog):
    def __init__(
        self,
        *,
        sensor_service: MaintenanceSensorService,
        sensor_reading_service: MaintenanceSensorReadingService,
        sensor_source_mapping_service: MaintenanceSensorSourceMappingService,
        integration_source_service: MaintenanceIntegrationSourceService,
        site_labels: dict[str, str],
        asset_labels: dict[str, str],
        component_labels: dict[str, str],
        system_labels: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sensor_service = sensor_service
        self._sensor_reading_service = sensor_reading_service
        self._sensor_source_mapping_service = sensor_source_mapping_service
        self._integration_source_service = integration_source_service
        self._site_labels = site_labels
        self._asset_labels = asset_labels
        self._component_labels = component_labels
        self._system_labels = system_labels

        self.setWindowTitle("Sensor Details")
        self.resize(980, 660)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        self.title_label = QLabel("No sensor selected")
        self.title_label.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        root.addWidget(self.title_label)

        self.workbench = MaintenanceWorkbenchNavigator(object_name="maintenanceSensorDetailWorkbench", parent=self)
        self.overview_widget, self.overview_summary = self._build_overview_widget()
        self.readings_widget, self.readings_table = self._build_readings_widget()
        self.mappings_widget, self.mapping_table = self._build_mappings_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(
                    key="overview",
                    label="Overview",
                    widget=self.overview_widget,
                ),
                MaintenanceWorkbenchSection(
                    key="readings",
                    label="Recent Readings",
                    widget=self.readings_widget,
                ),
                MaintenanceWorkbenchSection(
                    key="mappings",
                    label="Source Mappings",
                    widget=self.mappings_widget,
                ),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

    def load_sensor(self, sensor_id: str) -> None:
        sensor = self._sensor_service.get_sensor(sensor_id)
        readings = self._sensor_reading_service.list_readings(sensor_id=sensor.id)
        mappings = self._sensor_source_mapping_service.list_mappings(sensor_id=sensor.id, active_only=None)
        integration_rows = self._integration_source_service.list_sources(active_only=None)

        self.title_label.setText(f"{sensor.sensor_code} - {sensor.sensor_name}")
        self.overview_summary.setText(
            "\n".join(
                [
                    f"Anchor: {self._anchor_label(sensor)}",
                    f"Type / Source: {sensor.sensor_type.replace('_', ' ').title() or '-'} / {sensor.source_type.replace('_', ' ').title() or '-'}",
                    f"Tag / Key: {sensor.sensor_tag or '-'} / {sensor.source_key or '-'}",
                    f"Current value: {sensor.current_value if sensor.current_value is not None else '-'} {sensor.unit or ''}".strip(),
                    f"Latest quality: {sensor.last_quality_state.value.title()} | Last read: {format_timestamp(sensor.last_read_at)}",
                    f"Source name: {sensor.source_name or '-'}",
                    f"Notes: {sensor.notes or '-'}",
                ]
            )
        )

        self.readings_table.setRowCount(len(readings[:10]))
        for row_index, row in enumerate(readings[:10]):
            values = (
                str(row.reading_value),
                row.reading_unit,
                row.quality_state.value.title(),
                format_timestamp(row.reading_timestamp),
                row.source_batch_id or "-",
            )
            for column, value in enumerate(values):
                self.readings_table.setItem(row_index, column, QTableWidgetItem(value))

        self.mapping_table.setRowCount(len(mappings))
        for row_index, row in enumerate(mappings):
            source_label = next(
                (
                    f"{source.integration_code} - {source.name}"
                    for source in integration_rows
                    if source.id == row.integration_source_id
                ),
                row.integration_source_id,
            )
            values = (
                source_label,
                row.external_measurement_key or "-",
                row.external_equipment_key or "-",
                "Yes" if row.is_active else "No",
            )
            for column, value in enumerate(values):
                self.mapping_table.setItem(row_index, column, QTableWidgetItem(value))
        self.workbench.set_current_section("overview")

    def _build_overview_widget(self) -> tuple[QWidget, QLabel]:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceSensorDialogOverviewSurface",
            alt=False,
        )
        title = QLabel("Sensor Overview")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        summary = QLabel("Select a sensor to inspect its maintenance anchor, quality, and latest snapshot.")
        summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        summary.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(summary)
        return widget, summary

    def _build_readings_widget(self) -> tuple[QWidget, object]:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceSensorDialogReadingsSurface",
            alt=False,
        )
        title = QLabel("Recent Readings")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Latest sensor readings captured for the selected maintenance point.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        table = build_admin_table(
            headers=("Value", "Unit", "Quality", "Timestamp", "Batch"),
            resize_modes=(
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._stretch(),
            ),
        )
        layout.addWidget(table)
        return widget, table

    def _build_mappings_widget(self) -> tuple[QWidget, object]:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceSensorDialogMappingsSurface",
            alt=False,
        )
        title = QLabel("Source Mappings")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("External equipment and measurement keys linked to the selected sensor.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        table = build_admin_table(
            headers=("Integration", "Measurement", "Equipment", "Active"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(table)
        return widget, table

    def _anchor_label(self, sensor) -> str:
        if sensor.component_id:
            return self._component_labels.get(sensor.component_id, sensor.component_id)
        if sensor.asset_id:
            return self._asset_labels.get(sensor.asset_id, sensor.asset_id)
        if sensor.system_id:
            return self._system_labels.get(sensor.system_id, sensor.system_id)
        return self._site_labels.get(sensor.site_id, sensor.site_id)

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceSensorDetailDialog"]
