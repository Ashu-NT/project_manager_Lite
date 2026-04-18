from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDialog,
)

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.maintenance_management import (
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenanceLocationService,
    MaintenanceSystemService,
)
from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org import SiteService
from ui.modules.maintenance_management.asset_library.detail_dialog import MaintenanceAssetLibraryDetailDialog
from ui.modules.maintenance_management.asset_library.edit_dialogs import MaintenanceAssetEditDialog
from ui.modules.maintenance_management.shared import (
    build_maintenance_header,
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


class MaintenanceAssetLibraryTab(QWidget):
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
        self._can_manage = has_permission(user_session, "maintenance.manage")
        self._all_assets = []
        self._site_labels: dict[str, str] = {}
        self._location_labels: dict[str, str] = {}
        self._system_labels: dict[str, str] = {}
        self._detail_dialog: MaintenanceAssetLibraryDetailDialog | None = None
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
        self.active_badge = make_meta_badge("0 active")
        self.access_badge = make_meta_badge("Manage Enabled" if self._can_manage else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenanceAssetLibraryHeaderCard",
            eyebrow_text="MAINTENANCE LIBRARIES",
            title_text="Asset Library",
            subtitle_text="Author maintenance assets and open the detail popup to manage reusable components under each selected asset.",
            badges=(self.context_badge, self.asset_count_badge, self.active_badge, self.access_badge),
        )

        actions, actions_layout = build_admin_surface_card(
            object_name="maintenanceAssetLibraryActionSurface",
            alt=False,
        )
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_new_asset = QPushButton("New Asset")
        self.btn_edit_asset = QPushButton("Edit Asset")
        self.btn_toggle_active = QPushButton("Toggle Active")
        self.btn_open_detail = QPushButton("Open Detail")
        for button, variant in (
            (self.btn_new_asset, "primary"),
            (self.btn_edit_asset, "secondary"),
            (self.btn_toggle_active, "secondary"),
            (self.btn_open_detail, "secondary"),
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style(variant))
            action_row.addWidget(button)
        action_row.addStretch(1)
        actions_layout.addLayout(action_row)
        root.addWidget(actions)

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceAssetLibraryControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All locations | All systems | Active only | All categories")
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
        filter_row = QHBoxLayout(self.filter_panel)
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(CFG.SPACING_MD)
        self.site_combo = QComboBox()
        self.location_combo = QComboBox()
        self.system_combo = QComboBox()
        self.status_combo = QComboBox()
        self.status_combo.addItem("Active only", True)
        self.status_combo.addItem("Inactive only", False)
        self.status_combo.addItem("All statuses", None)
        self.category_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, name, model, serial, status, or strategy")
        for label, widget in (
            ("Site", self.site_combo),
            ("Location", self.location_combo),
            ("System", self.system_combo),
            ("Lifecycle", self.status_combo),
            ("Category", self.category_combo),
        ):
            filter_row.addWidget(QLabel(label))
            filter_row.addWidget(widget)
        filter_row.addWidget(QLabel("Search"))
        filter_row.addWidget(self.search_edit, 1)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Assets", "-", "Visible in current library filter", CFG.COLOR_ACCENT)
        self.active_card = KpiCard("Active", "-", "Ready for use", CFG.COLOR_SUCCESS)
        self.critical_card = KpiCard("Critical", "-", "Critical maintenance assets", CFG.COLOR_WARNING)
        self.component_card = KpiCard("Components", "-", "Linked reusable component records", CFG.COLOR_ACCENT)
        for card in (self.total_card, self.active_card, self.critical_card, self.component_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        panel, layout = build_admin_surface_card(
            object_name="maintenanceAssetLibraryGridSurface",
            alt=False,
        )
        title = QLabel("Asset Authoring Queue")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel(
            "Create and maintain asset master records here, then open the detail popup to manage component definitions."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.selection_summary = QLabel(
            "Select an asset, then click Open Detail to inspect metadata and manage components."
        )
        self.selection_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.selection_summary.setWordWrap(True)
        layout.addWidget(self.selection_summary)
        self.table = build_admin_table(
            headers=("Code", "Name", "Site", "Location", "System", "Category", "Status", "Active"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.table)
        root.addWidget(panel, 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.location_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.reload_data)
        )
        self.system_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.reload_rows)
        )
        self.status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.reload_rows)
        )
        self.category_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.reload_rows)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.reload_rows)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.reload_data)
        )
        self.btn_new_asset.clicked.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.create_asset)
        )
        self.btn_edit_asset.clicked.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.edit_asset)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Asset Library", callback=self.toggle_active)
        )
        self.btn_open_detail.clicked.connect(
            make_guarded_slot(self, title="Asset Library", callback=self._open_detail_dialog)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_asset, self.btn_edit_asset, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="maintenance.manage")
        self._sync_actions()

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_location_id = selected_combo_value(self.location_combo)
        selected_system_id = selected_combo_value(self.system_combo)
        selected_category = selected_combo_value(self.category_combo)
        try:
            sites = self._site_service.list_sites(active_only=None)
            locations = self._location_service.list_locations(active_only=None, site_id=selected_site_id)
            systems = self._system_service.list_systems(active_only=None, site_id=selected_site_id)
            all_assets = self._asset_service.list_assets(
                active_only=None,
                site_id=selected_site_id,
                location_id=selected_location_id,
                system_id=selected_system_id,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Asset Library", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Asset Library", f"Failed to load asset-library filters: {exc}")
            return

        self._all_assets = all_assets
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
            options=[(f"{row.location_code} - {row.name}", row.id) for row in locations],
            selected_value=selected_location_id,
        )
        reset_combo_options(
            self.system_combo,
            placeholder="All systems",
            options=[(f"{row.system_code} - {row.name}", row.id) for row in systems],
            selected_value=selected_system_id,
        )
        categories = sorted({row.asset_category for row in all_assets if row.asset_category})
        reset_combo_options(
            self.category_combo,
            placeholder="All categories",
            options=[(category, category) for category in categories],
            selected_value=selected_category,
        )
        self.reload_rows()

    def reload_rows(self) -> None:
        selected_asset_id = self._selected_asset_id()
        try:
            rows = self._asset_service.search_assets(
                search_text=self.search_edit.text(),
                active_only=self.status_combo.currentData(),
                site_id=selected_combo_value(self.site_combo),
                location_id=selected_combo_value(self.location_combo),
                system_id=selected_combo_value(self.system_combo),
                asset_category=selected_combo_value(self.category_combo),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Asset Library", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Asset Library", f"Failed to refresh asset-library rows: {exc}")
            return

        component_total = sum(
            len(self._component_service.list_components(active_only=None, asset_id=row.id))
            for row in rows
        )
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.asset_count_badge.setText(f"{len(rows)} assets")
        self.active_badge.setText(f"{sum(1 for row in rows if row.is_active)} active")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.location_combo.currentText()} | "
            f"{self.system_combo.currentText()} | {self.status_combo.currentText()} | {self.category_combo.currentText()}"
            + (f" | Search: {self.search_edit.text().strip()}" if self.search_edit.text().strip() else "")
        )
        self.total_card.set_value(str(len(rows)))
        self.active_card.set_value(str(sum(1 for row in rows if row.is_active)))
        self.critical_card.set_value(str(sum(1 for row in rows if row.criticality.value.upper() == "CRITICAL")))
        self.component_card.set_value(str(component_total))
        self._populate_table(rows, selected_asset_id=selected_asset_id)

    def create_asset(self) -> None:
        dialog = MaintenanceAssetEditDialog(
            site_options=self._site_options(),
            locations=self._all_locations(),
            systems=self._all_systems(),
            assets=self._asset_service.list_assets(active_only=None),
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                self._asset_service.create_asset(
                    site_id=dialog.site_id,
                    location_id=dialog.location_id,
                    asset_code=dialog.asset_code,
                    name=dialog.name,
                    system_id=dialog.system_id,
                    description=dialog.description,
                    parent_asset_id=dialog.parent_asset_id,
                    asset_type=dialog.asset_type,
                    asset_category=dialog.asset_category,
                    criticality=dialog.criticality,
                    status=dialog.status,
                    model_number=dialog.model_number,
                    serial_number=dialog.serial_number,
                    barcode=dialog.barcode,
                    maintenance_strategy=dialog.maintenance_strategy,
                    service_level=dialog.service_level,
                    requires_shutdown_for_major_work=dialog.requires_shutdown_for_major_work,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Asset Library", str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Asset Library", f"Failed to create asset: {exc}")
                return
            break
        self.reload_data()

    def edit_asset(self) -> None:
        asset = self._selected_asset()
        if asset is None:
            QMessageBox.information(self, "Asset Library", "Select an asset to edit.")
            return
        dialog = MaintenanceAssetEditDialog(
            site_options=self._site_options(),
            locations=self._all_locations(),
            systems=self._all_systems(),
            assets=self._asset_service.list_assets(active_only=None),
            asset=asset,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                self._asset_service.update_asset(
                    asset.id,
                    site_id=dialog.site_id,
                    location_id=dialog.location_id,
                    asset_code=dialog.asset_code,
                    name=dialog.name,
                    system_id=dialog.system_id or "",
                    description=dialog.description,
                    parent_asset_id=dialog.parent_asset_id or "",
                    asset_type=dialog.asset_type,
                    asset_category=dialog.asset_category,
                    criticality=dialog.criticality,
                    status=dialog.status,
                    model_number=dialog.model_number,
                    serial_number=dialog.serial_number,
                    barcode=dialog.barcode,
                    maintenance_strategy=dialog.maintenance_strategy,
                    service_level=dialog.service_level,
                    requires_shutdown_for_major_work=dialog.requires_shutdown_for_major_work,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                    expected_version=asset.version,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Asset Library", str(exc))
                continue
            except ConcurrencyError as exc:
                QMessageBox.warning(self, "Asset Library", str(exc))
                self.reload_data()
                return
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Asset Library", f"Failed to update asset: {exc}")
                return
            break
        self.reload_data()

    def toggle_active(self) -> None:
        asset = self._selected_asset()
        if asset is None:
            QMessageBox.information(self, "Asset Library", "Select an asset to update.")
            return
        try:
            self._asset_service.update_asset(
                asset.id,
                is_active=not asset.is_active,
                expected_version=asset.version,
            )
        except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Asset Library", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Asset Library", f"Failed to update asset: {exc}")
            return
        self.reload_data()

    def _populate_table(self, rows, *, selected_asset_id: str | None) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        selected_row = -1
        for row_index, asset in enumerate(rows):
            values = (
                asset.asset_code,
                asset.name,
                self._site_labels.get(asset.site_id, asset.site_id),
                self._location_labels.get(asset.location_id, asset.location_id),
                self._system_labels.get(asset.system_id or "", asset.system_id or "-"),
                asset.asset_category or "-",
                asset.status.value.title(),
                "Yes" if asset.is_active else "No",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, asset.id)
                self.table.setItem(row_index, column, item)
            if selected_asset_id and asset.id == selected_asset_id:
                selected_row = row_index
        self.table.blockSignals(False)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
        self._sync_actions()

    def _selected_asset_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_asset(self):
        asset_id = self._selected_asset_id()
        if not asset_id:
            return None
        try:
            return self._asset_service.get_asset(asset_id)
        except Exception:  # noqa: BLE001
            return None

    def _open_detail_dialog(self) -> None:
        asset_id = self._selected_asset_id()
        if not asset_id:
            QMessageBox.information(self, "Asset Library", "Select an asset to open its detail view.")
            return
        dialog = MaintenanceAssetLibraryDetailDialog(
            asset_service=self._asset_service,
            component_service=self._component_service,
            site_labels=self._site_labels,
            location_labels=self._location_labels,
            system_labels=self._system_labels,
            can_manage=self._can_manage,
            parent=self,
        )
        dialog.load_asset(asset_id)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._detail_dialog = dialog

    def _sync_actions(self) -> None:
        asset = self._selected_asset()
        if asset is None:
            self.selection_summary.setText(
                "Select an asset, then click Open Detail to inspect metadata and manage components."
            )
            self.btn_new_asset.setEnabled(self._can_manage)
            self.btn_edit_asset.setEnabled(False)
            self.btn_toggle_active.setEnabled(False)
            self.btn_open_detail.setEnabled(False)
            return
        component_count = len(self._component_service.list_components(active_only=None, asset_id=asset.id))
        self.selection_summary.setText(
            f"Selected: {asset.asset_code} | Status: {asset.status.value.title()} | Components: {component_count}"
        )
        self.btn_new_asset.setEnabled(self._can_manage)
        self.btn_edit_asset.setEnabled(self._can_manage)
        self.btn_toggle_active.setEnabled(self._can_manage)
        self.btn_open_detail.setEnabled(True)

    def _site_options(self) -> list[tuple[str, str]]:
        return [(f"{site.site_code} - {site.name}", site.id) for site in self._site_service.list_sites(active_only=None)]

    def _all_locations(self):
        return self._location_service.list_locations(active_only=None)

    def _all_systems(self):
        return self._system_service.list_systems(active_only=None)

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

    def _on_site_changed(self) -> None:
        self.reload_data()

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


__all__ = ["MaintenanceAssetLibraryTab"]
