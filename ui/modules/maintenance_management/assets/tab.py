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
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenanceLocationService,
    MaintenanceSystemService,
)
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org import SiteService
from ui.modules.maintenance_management.shared import (
    build_maintenance_header,
    make_accent_badge,
    make_meta_badge,
    reset_combo_options,
    selected_combo_value,
)
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.modules.project_management.dashboard.widgets import KpiCard
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceAssetsTab(QWidget):
    def __init__(
        self,
        *,
        asset_service: MaintenanceAssetService,
        component_service: MaintenanceAssetComponentService,
        site_service: SiteService,
        location_service: MaintenanceLocationService,
        system_service: MaintenanceSystemService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._asset_service = asset_service
        self._component_service = component_service
        self._site_service = site_service
        self._location_service = location_service
        self._system_service = system_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._site_labels: dict[str, str] = {}
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
        self.asset_count_badge = make_meta_badge("0 assets")
        self.component_count_badge = make_meta_badge("0 components")
        build_maintenance_header(
            root=root,
            object_name="maintenanceAssetsHeaderCard",
            eyebrow_text="MAINTENANCE RECORDS",
            title_text="Assets",
            subtitle_text="Browse maintenance assets, inspect hierarchy context, and review linked components from the first phase-1 runtime.",
            badges=(self.context_badge, self.asset_count_badge, self.component_count_badge),
        )

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceAssetsControlSurface",
            alt=True,
        )
        filter_row = QGridLayout()
        filter_row.setHorizontalSpacing(CFG.SPACING_MD)
        filter_row.setVerticalSpacing(CFG.SPACING_SM)
        self.site_combo = QComboBox()
        self.location_combo = QComboBox()
        self.system_combo = QComboBox()
        self.status_combo = QComboBox()
        self.category_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, name, model, serial, status, or strategy")
        self.status_combo.addItem("Active only", True)
        self.status_combo.addItem("Inactive only", False)
        self.status_combo.addItem("All statuses", None)
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Location"), 0, 2)
        filter_row.addWidget(self.location_combo, 0, 3)
        filter_row.addWidget(QLabel("System"), 1, 0)
        filter_row.addWidget(self.system_combo, 1, 1)
        filter_row.addWidget(QLabel("Lifecycle"), 1, 2)
        filter_row.addWidget(self.status_combo, 1, 3)
        filter_row.addWidget(QLabel("Category"), 2, 0)
        filter_row.addWidget(self.category_combo, 2, 1)
        filter_row.addWidget(QLabel("Search"), 2, 2)
        filter_row.addWidget(self.search_edit, 2, 3)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_refresh.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)

        self.filter_summary = QLabel("")
        self.filter_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.filter_summary.setWordWrap(True)
        controls_layout.addWidget(self.filter_summary)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_assets_card = KpiCard("Assets", "-", "Visible in current scope", CFG.COLOR_ACCENT)
        self.active_assets_card = KpiCard("Active", "-", "Ready for maintenance work", CFG.COLOR_SUCCESS)
        self.critical_assets_card = KpiCard("Critical", "-", "Criticality = critical", CFG.COLOR_WARNING)
        self.components_card = KpiCard("Components", "-", "Linked to listed assets", CFG.COLOR_ACCENT)
        for card in (
            self.total_assets_card,
            self.active_assets_card,
            self.critical_assets_card,
            self.components_card,
        ):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)
        content_row.addWidget(self._build_assets_panel(), 3)
        content_row.addWidget(self._build_details_panel(), 2)
        root.addLayout(content_row, 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.location_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Assets", callback=self.reload_data)
        )
        self.system_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Assets", callback=self.reload_assets)
        )
        self.status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Assets", callback=self.reload_assets)
        )
        self.category_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Assets", callback=self.reload_assets)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Maintenance Assets", callback=self.reload_assets)
        )
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Assets", callback=self.reload_data)
        )
        self.asset_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Assets", callback=self._on_asset_selection_changed)
        )

    def _build_assets_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceAssetsGridSurface",
            alt=False,
        )
        title = QLabel("Asset Register")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Filtered maintenance assets in the current organization and scope.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.asset_table = build_admin_table(
            headers=("Asset", "Site", "Location", "System", "Category", "Status", "Criticality"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.asset_table)
        return panel

    def _build_details_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceAssetDetailSurface",
            alt=False,
        )
        title = QLabel("Selected Asset")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Metadata, hierarchy context, and linked components for the current asset.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.detail_title = QLabel("No asset selected")
        self.detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        layout.addWidget(self.detail_title)
        self.detail_summary = QLabel("Select an asset to inspect lifecycle, hierarchy, and equipment context.")
        self.detail_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.detail_summary.setWordWrap(True)
        layout.addWidget(self.detail_summary)
        component_title = QLabel("Components")
        component_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(component_title)
        self.component_table = build_admin_table(
            headers=("Component", "Type", "Status", "Critical"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.component_table)
        return panel

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_location_id = selected_combo_value(self.location_combo)
        selected_system_id = selected_combo_value(self.system_combo)
        selected_category = selected_combo_value(self.category_combo)
        selected_asset_id = self._selected_asset_id()
        try:
            sites = self._site_service.list_sites(active_only=None)
            locations = self._location_service.list_locations(active_only=True, site_id=selected_site_id)
            systems = self._system_service.list_systems(active_only=True, site_id=selected_site_id)
            category_rows = self._asset_service.list_assets(
                active_only=None,
                site_id=selected_site_id,
                location_id=selected_location_id,
                system_id=selected_system_id,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Assets", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Assets", f"Failed to load maintenance asset filters: {exc}")
            return

        self._site_labels = {site.id: site.name for site in sites}
        self._location_labels = {location.id: location.name for location in locations}
        self._system_labels = {system.id: system.name for system in systems}

        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{site.site_code} - {site.name}", site.id) for site in sites],
            selected_value=selected_site_id,
        )
        reset_combo_options(
            self.location_combo,
            placeholder="All locations",
            options=[(f"{location.location_code} - {location.name}", location.id) for location in locations],
            selected_value=selected_location_id,
        )
        reset_combo_options(
            self.system_combo,
            placeholder="All systems",
            options=[(f"{system.system_code} - {system.name}", system.id) for system in systems],
            selected_value=selected_system_id,
        )
        categories = sorted({row.asset_category for row in category_rows if row.asset_category})
        reset_combo_options(
            self.category_combo,
            placeholder="All categories",
            options=[(category, category) for category in categories],
            selected_value=selected_category,
        )
        self.reload_assets(selected_asset_id=selected_asset_id)

    def reload_assets(self, *, selected_asset_id: str | None = None) -> None:
        selected_asset_id = selected_asset_id or self._selected_asset_id()
        try:
            rows = self._asset_service.search_assets(
                search_text=self.search_edit.text(),
                active_only=self._selected_active_only(),
                site_id=selected_combo_value(self.site_combo),
                location_id=selected_combo_value(self.location_combo),
                system_id=selected_combo_value(self.system_combo),
                asset_category=selected_combo_value(self.category_combo),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Assets", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Assets", f"Failed to load maintenance assets: {exc}")
            return

        component_total = 0
        for asset in rows:
            component_total += len(
                self._component_service.list_components(active_only=None, asset_id=asset.id)
            )
        self.total_assets_card.set_value(str(len(rows)))
        self.active_assets_card.set_value(str(sum(1 for row in rows if row.is_active)))
        self.critical_assets_card.set_value(
            str(sum(1 for row in rows if str(row.criticality.value).upper() == "CRITICAL"))
        )
        self.components_card.set_value(str(component_total))
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.asset_count_badge.setText(f"{len(rows)} assets")
        self.component_count_badge.setText(f"{component_total} components")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.location_combo.currentText()} | "
            f"{self.system_combo.currentText()} | {self.status_combo.currentText()} | "
            f"{self.category_combo.currentText()}"
        )
        self._populate_asset_table(rows, selected_asset_id=selected_asset_id)

    def _populate_asset_table(self, rows, *, selected_asset_id: str | None) -> None:
        self.asset_table.blockSignals(True)
        self.asset_table.setRowCount(len(rows))
        selected_row = 0 if rows else -1
        for row_index, asset in enumerate(rows):
            values = (
                f"{asset.asset_code} - {asset.name}",
                self._site_labels.get(asset.site_id, asset.site_id),
                self._location_labels.get(asset.location_id, asset.location_id),
                self._system_labels.get(asset.system_id or "", asset.system_id or "-"),
                asset.asset_category or "-",
                asset.status.value.title(),
                asset.criticality.value.title(),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, asset.id)
                self.asset_table.setItem(row_index, column, item)
            if selected_asset_id and asset.id == selected_asset_id:
                selected_row = row_index
        self.asset_table.blockSignals(False)
        if selected_row >= 0:
            self.asset_table.selectRow(selected_row)
            self._refresh_asset_details(rows[selected_row].id)
            return
        self._clear_asset_details()

    def _on_site_changed(self) -> None:
        self.reload_data()

    def _on_asset_selection_changed(self) -> None:
        asset_id = self._selected_asset_id()
        if asset_id:
            self._refresh_asset_details(asset_id)
            return
        self._clear_asset_details()

    def _refresh_asset_details(self, asset_id: str) -> None:
        try:
            asset = self._asset_service.get_asset(asset_id)
            components = self._component_service.list_components(active_only=None, asset_id=asset.id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Assets", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Assets", f"Failed to load maintenance asset details: {exc}")
            return

        self.detail_title.setText(f"{asset.asset_code} - {asset.name}")
        self.detail_summary.setText(
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

    def _clear_asset_details(self) -> None:
        self.detail_title.setText("No asset selected")
        self.detail_summary.setText("Select an asset to inspect lifecycle, hierarchy, and equipment context.")
        self.component_table.setRowCount(0)

    def _selected_asset_id(self) -> str | None:
        row = self.asset_table.currentRow()
        if row < 0:
            return None
        item = self.asset_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_active_only(self) -> bool | None:
        return self.status_combo.currentData()

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


__all__ = ["MaintenanceAssetsTab"]
