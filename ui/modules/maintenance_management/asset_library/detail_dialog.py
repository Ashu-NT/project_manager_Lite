from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.modules.maintenance_management import (
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
)
from core.modules.maintenance_management.domain import MaintenanceAssetComponent
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from ui.modules.maintenance_management.asset_library.edit_dialogs import MaintenanceAssetComponentEditDialog
from ui.modules.maintenance_management.shared import (
    MaintenanceWorkbenchNavigator,
    MaintenanceWorkbenchSection,
    build_maintenance_header,
    format_timestamp,
    make_accent_badge,
    make_meta_badge,
)
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import apply_permission_hint, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceAssetLibraryDetailDialog(QDialog):
    def __init__(
        self,
        *,
        asset_service: MaintenanceAssetService,
        component_service: MaintenanceAssetComponentService,
        site_labels: dict[str, str],
        location_labels: dict[str, str],
        system_labels: dict[str, str],
        can_manage: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._asset_service = asset_service
        self._component_service = component_service
        self._site_labels = site_labels
        self._location_labels = location_labels
        self._system_labels = system_labels
        self._can_manage = can_manage
        self._current_asset_id: str | None = None
        self._component_rows: list[MaintenanceAssetComponent] = []

        self.setWindowTitle("Asset Library Detail")
        self.resize(1120, 760)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        self.context_badge = make_accent_badge("Asset")
        self.component_count_badge = make_meta_badge("0 components")
        self.active_badge = make_meta_badge("Inactive")
        self.access_badge = make_meta_badge("Manage Enabled" if self._can_manage else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenanceAssetLibraryDetailHeaderCard",
            eyebrow_text="MAINTENANCE LIBRARIES",
            title_text="Asset Library Detail",
            subtitle_text="Inspect asset metadata and manage reusable component records without crowding the authoring queue.",
            badges=(self.context_badge, self.component_count_badge, self.active_badge, self.access_badge),
        )

        self.workbench = MaintenanceWorkbenchNavigator(
            object_name="maintenanceAssetLibraryDetailWorkbench",
            parent=self,
        )
        self.overview_widget = self._build_overview_widget()
        self.components_widget = self._build_components_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(key="overview", label="Overview", widget=self.overview_widget),
                MaintenanceWorkbenchSection(key="components", label="Components", widget=self.components_widget),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

        self.component_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Asset Library Detail", callback=self._sync_component_actions)
        )
        self.btn_new_component.clicked.connect(
            make_guarded_slot(self, title="Asset Library Detail", callback=self._create_component)
        )
        self.btn_edit_component.clicked.connect(
            make_guarded_slot(self, title="Asset Library Detail", callback=self._edit_component)
        )
        self.btn_toggle_component.clicked.connect(
            make_guarded_slot(self, title="Asset Library Detail", callback=self._toggle_component_active)
        )
        apply_permission_hint(self.btn_new_component, allowed=self._can_manage, missing_permission="maintenance.manage")
        apply_permission_hint(self.btn_edit_component, allowed=self._can_manage, missing_permission="maintenance.manage")
        apply_permission_hint(
            self.btn_toggle_component,
            allowed=self._can_manage,
            missing_permission="maintenance.manage",
        )
        domain_events.domain_changed.connect(self._on_domain_change)
        self._sync_component_actions()

    def _build_overview_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceAssetLibraryDetailOverviewSurface",
            alt=False,
        )
        title = QLabel("Asset Overview")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel(
            "Hierarchy, lifecycle, category, and strategy stay here while component authoring stays in its own focused section."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        overview_grid = QGridLayout()
        overview_grid.setHorizontalSpacing(CFG.SPACING_MD)
        overview_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.overview_labels: dict[str, QLabel] = {}
        fields = (
            ("Code", "code"),
            ("Name", "name"),
            ("Site", "site"),
            ("Location", "location"),
            ("System", "system"),
            ("Category", "category"),
            ("Type", "type"),
            ("Status", "status"),
            ("Criticality", "criticality"),
            ("Strategy", "strategy"),
            ("Service Level", "service_level"),
            ("Model / Serial", "model_serial"),
            ("Created", "created_at"),
            ("Updated", "updated_at"),
        )
        for index, (label, key) in enumerate(fields):
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            self.overview_labels[key] = value_label
            overview_grid.addWidget(QLabel(label), index, 0, Qt.AlignTop)
            overview_grid.addWidget(value_label, index, 1)
        layout.addLayout(overview_grid)

        self.description_label = QLabel("-")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.notes_label = QLabel("-")
        self.notes_label.setWordWrap(True)
        self.notes_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(QLabel("Description"))
        layout.addWidget(self.description_label)
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.notes_label)
        return widget

    def _build_components_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceAssetLibraryDetailComponentsSurface",
            alt=False,
        )
        title = QLabel("Components")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Manage the reusable component register that hangs under the selected asset.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.component_summary = QLabel("Select a component to edit or toggle it.")
        self.component_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.component_summary.setWordWrap(True)
        layout.addWidget(self.component_summary)
        self.component_table = build_admin_table(
            headers=("Code", "Name", "Type", "Status", "Critical", "Active"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.component_table)
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_new_component = QPushButton("New Component")
        self.btn_edit_component = QPushButton("Edit Component")
        self.btn_toggle_component = QPushButton("Toggle Active")
        for button in (self.btn_new_component, self.btn_edit_component, self.btn_toggle_component):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style("secondary"))
            action_row.addWidget(button)
        action_row.addStretch(1)
        layout.addLayout(action_row)
        return widget

    def load_asset(self, asset_id: str, *, selected_component_id: str | None = None) -> None:
        self._current_asset_id = asset_id
        try:
            asset = self._asset_service.get_asset(asset_id)
            components = self._component_service.list_components(active_only=None, asset_id=asset.id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Asset Library Detail", str(exc))
            return
        except NotFoundError as exc:
            QMessageBox.warning(self, "Asset Library Detail", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Asset Library Detail", f"Failed to load asset detail: {exc}")
            return

        self._component_rows = components
        self.context_badge.setText(f"Asset: {asset.asset_code}")
        self.component_count_badge.setText(f"{len(components)} components")
        self.active_badge.setText("Active" if asset.is_active else "Inactive")
        self.setWindowTitle(f"Asset Library Detail - {asset.asset_code}")
        self._populate_overview(asset)
        self._populate_component_table(selected_component_id=selected_component_id)
        self.workbench.set_current_section("overview")

    def _populate_overview(self, asset) -> None:
        self.overview_labels["code"].setText(asset.asset_code)
        self.overview_labels["name"].setText(asset.name)
        self.overview_labels["site"].setText(self._site_labels.get(asset.site_id, asset.site_id))
        self.overview_labels["location"].setText(self._location_labels.get(asset.location_id, asset.location_id))
        self.overview_labels["system"].setText(self._system_labels.get(asset.system_id or "", asset.system_id or "-"))
        self.overview_labels["category"].setText(asset.asset_category or "-")
        self.overview_labels["type"].setText(asset.asset_type or "-")
        self.overview_labels["status"].setText(asset.status.value.title())
        self.overview_labels["criticality"].setText(asset.criticality.value.title())
        self.overview_labels["strategy"].setText(asset.maintenance_strategy or "-")
        self.overview_labels["service_level"].setText(asset.service_level or "-")
        self.overview_labels["model_serial"].setText(
            f"{asset.model_number or '-'} / {asset.serial_number or '-'}"
        )
        self.overview_labels["created_at"].setText(format_timestamp(asset.created_at))
        self.overview_labels["updated_at"].setText(format_timestamp(asset.updated_at))
        self.description_label.setText(asset.description or "-")
        self.notes_label.setText(asset.notes or "-")

    def _populate_component_table(self, *, selected_component_id: str | None) -> None:
        self.component_table.blockSignals(True)
        self.component_table.setRowCount(len(self._component_rows))
        selected_row = -1
        for row_index, row in enumerate(self._component_rows):
            values = (
                row.component_code,
                row.name,
                row.component_type or "-",
                row.status.value.title(),
                "Yes" if row.is_critical_component else "No",
                "Yes" if row.is_active else "No",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.component_table.setItem(row_index, column, item)
            if selected_component_id and row.id == selected_component_id:
                selected_row = row_index
        self.component_table.blockSignals(False)
        if selected_row >= 0:
            self.component_table.selectRow(selected_row)
        else:
            self.component_table.clearSelection()
        self._sync_component_actions()

    def _create_component(self) -> None:
        if not self._current_asset_id:
            return
        dialog = MaintenanceAssetComponentEditDialog(
            components=self._component_rows,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                row = self._component_service.create_component(
                    asset_id=self._current_asset_id,
                    component_code=dialog.component_code,
                    name=dialog.name,
                    description=dialog.description,
                    parent_component_id=dialog.parent_component_id,
                    component_type=dialog.component_type,
                    status=dialog.status,
                    manufacturer_part_number=dialog.manufacturer_part_number,
                    supplier_part_number=dialog.supplier_part_number,
                    model_number=dialog.model_number,
                    serial_number=dialog.serial_number,
                    expected_life_hours=dialog.expected_life_hours,
                    expected_life_cycles=dialog.expected_life_cycles,
                    is_critical_component=dialog.is_critical_component,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Asset Library Detail", str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Asset Library Detail", f"Failed to create component: {exc}")
                return
            self.load_asset(self._current_asset_id, selected_component_id=row.id)
            self.workbench.set_current_section("components")
            return

    def _edit_component(self) -> None:
        component = self._selected_component()
        if component is None:
            QMessageBox.information(self, "Asset Library Detail", "Select a component to edit.")
            return
        dialog = MaintenanceAssetComponentEditDialog(
            components=self._component_rows,
            component=component,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                row = self._component_service.update_component(
                    component.id,
                    component_code=dialog.component_code,
                    name=dialog.name,
                    description=dialog.description,
                    parent_component_id=dialog.parent_component_id or "",
                    component_type=dialog.component_type,
                    status=dialog.status,
                    manufacturer_part_number=dialog.manufacturer_part_number,
                    supplier_part_number=dialog.supplier_part_number,
                    model_number=dialog.model_number,
                    serial_number=dialog.serial_number,
                    expected_life_hours=dialog.expected_life_hours,
                    expected_life_cycles=dialog.expected_life_cycles,
                    is_critical_component=dialog.is_critical_component,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                    expected_version=component.version,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Asset Library Detail", str(exc))
                continue
            except ConcurrencyError as exc:
                QMessageBox.warning(self, "Asset Library Detail", str(exc))
                self.load_asset(self._current_asset_id or "", selected_component_id=component.id)
                return
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Asset Library Detail", f"Failed to update component: {exc}")
                return
            self.load_asset(self._current_asset_id or "", selected_component_id=row.id)
            self.workbench.set_current_section("components")
            return

    def _toggle_component_active(self) -> None:
        component = self._selected_component()
        if component is None:
            QMessageBox.information(self, "Asset Library Detail", "Select a component to update.")
            return
        try:
            row = self._component_service.update_component(
                component.id,
                is_active=not component.is_active,
                expected_version=component.version,
            )
        except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Asset Library Detail", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Asset Library Detail", f"Failed to update component: {exc}")
            return
        self.load_asset(self._current_asset_id or "", selected_component_id=row.id)
        self.workbench.set_current_section("components")

    def _selected_component(self) -> MaintenanceAssetComponent | None:
        component_id = self._selected_component_id()
        if not component_id:
            return None
        return next((row for row in self._component_rows if row.id == component_id), None)

    def _selected_component_id(self) -> str | None:
        row = self.component_table.currentRow()
        if row < 0:
            return None
        item = self.component_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _sync_component_actions(self) -> None:
        component = self._selected_component()
        if component is None:
            self.component_summary.setText("Select a component to edit or toggle it.")
            self.btn_new_component.setEnabled(self._can_manage)
            self.btn_edit_component.setEnabled(False)
            self.btn_toggle_component.setEnabled(False)
            return
        self.component_summary.setText(
            f"Selected: {component.component_code} | Type: {component.component_type or '-'} | Active: {'Yes' if component.is_active else 'No'}"
        )
        self.btn_new_component.setEnabled(self._can_manage)
        self.btn_edit_component.setEnabled(self._can_manage)
        self.btn_toggle_component.setEnabled(self._can_manage)

    def _on_domain_change(self, event: DomainChangeEvent) -> None:
        if getattr(event, "scope_code", "") != "maintenance_management":
            return
        if self._current_asset_id is None:
            return
        if event.entity_type not in {"maintenance_asset", "maintenance_asset_component"}:
            return
        self.load_asset(self._current_asset_id, selected_component_id=self._selected_component_id())

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceAssetLibraryDetailDialog"]
