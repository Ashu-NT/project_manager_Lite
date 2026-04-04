from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QTableWidgetItem, QVBoxLayout, QWidget

from core.modules.maintenance_management import MaintenanceAssetComponentService, MaintenanceAssetService
from ui.modules.maintenance_management.shared import MaintenanceWorkbenchNavigator, MaintenanceWorkbenchSection
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceAssetDetailDialog(QDialog):
    def __init__(
        self,
        *,
        asset_service: MaintenanceAssetService,
        component_service: MaintenanceAssetComponentService,
        site_labels: dict[str, str],
        location_labels: dict[str, str],
        system_labels: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._asset_service = asset_service
        self._component_service = component_service
        self._site_labels = site_labels
        self._location_labels = location_labels
        self._system_labels = system_labels

        self.setWindowTitle("Asset Detail")
        self.resize(980, 680)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        self.title_label = QLabel("No asset selected")
        self.title_label.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        root.addWidget(self.title_label)

        self.workbench = MaintenanceWorkbenchNavigator(object_name="maintenanceAssetDetailWorkbench", parent=self)
        self.overview_widget, self.overview_summary = self._build_overview_widget()
        self.components_widget, self.component_table = self._build_components_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(key="overview", label="Overview", widget=self.overview_widget),
                MaintenanceWorkbenchSection(key="components", label="Components", widget=self.components_widget),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

    def load_asset(self, asset_id: str) -> None:
        asset = self._asset_service.get_asset(asset_id)
        components = self._component_service.list_components(active_only=None, asset_id=asset.id)

        self.title_label.setText(f"{asset.asset_code} - {asset.name}")
        self.overview_summary.setText(
            "\n".join(
                [
                    f"Site: {self._site_labels.get(asset.site_id, asset.site_id)}",
                    f"Location: {self._location_labels.get(asset.location_id, asset.location_id)}",
                    f"System: {self._system_labels.get(asset.system_id or '', asset.system_id or '-')}",
                    f"Lifecycle: {asset.status.value.title()} | Criticality: {asset.criticality.value.title()}",
                    f"Category: {asset.asset_category or '-'} | Type: {asset.asset_type or '-'}",
                    f"Model / Serial: {asset.model_number or '-'} / {asset.serial_number or '-'}",
                    f"Strategy: {asset.maintenance_strategy or '-'} | Service level: {asset.service_level or '-'}",
                    f"Shutdown required: {'Yes' if asset.requires_shutdown_for_major_work else 'No'}",
                    f"Notes: {asset.notes or '-'}",
                ]
            )
        )

        self.component_table.setRowCount(len(components))
        for row_index, component in enumerate(components):
            values = (
                f"{component.component_code} - {component.name}",
                component.component_type or "-",
                component.status.value.title(),
                "Yes" if component.is_critical_component else "No",
            )
            for column, value in enumerate(values):
                self.component_table.setItem(row_index, column, QTableWidgetItem(value))
        self.workbench.set_current_section("overview")

    def _build_overview_widget(self) -> tuple[QWidget, QLabel]:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceAssetDialogOverviewSurface",
            alt=False,
        )
        title = QLabel("Asset Overview")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        summary = QLabel("Select an asset to inspect maintenance hierarchy, lifecycle, and service context.")
        summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        summary.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(summary)
        return widget, summary

    def _build_components_widget(self) -> tuple[QWidget, object]:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceAssetDialogComponentsSurface",
            alt=False,
        )
        title = QLabel("Components")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Component records linked to the selected asset.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        table = build_admin_table(
            headers=("Component", "Type", "Status", "Critical"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(table)
        return widget, table

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceAssetDetailDialog"]
