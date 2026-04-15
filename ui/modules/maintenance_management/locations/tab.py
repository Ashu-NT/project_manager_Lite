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
from core.modules.maintenance_management import MaintenanceLocationService
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org import SiteService
from ui.modules.maintenance_management.locations.dialogs import MaintenanceLocationEditDialog
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
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceLocationsTab(QWidget):
    def __init__(
        self,
        *,
        location_service: MaintenanceLocationService,
        site_service: SiteService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._location_service = location_service
        self._site_service = site_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(user_session, "maintenance.manage")
        self._rows = []
        self._all_locations = []
        self._site_labels: dict[str, str] = {}
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
        self.count_badge = make_meta_badge("0 locations")
        self.active_badge = make_meta_badge("0 active")
        self.access_badge = make_meta_badge("Manage Enabled" if self._can_manage else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenanceLocationsHeaderCard",
            eyebrow_text="MAINTENANCE LIBRARIES",
            title_text="Locations",
            subtitle_text="Manage maintenance-owned location hierarchy records for areas, buildings, units, and other maintainable places.",
            badges=(self.context_badge, self.count_badge, self.active_badge, self.access_badge),
        )

        actions, actions_layout = build_admin_surface_card(
            object_name="maintenanceLocationsActionSurface",
            alt=False,
        )
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_new_location = QPushButton("New Location")
        self.btn_edit_location = QPushButton("Edit Location")
        self.btn_toggle_active = QPushButton("Toggle Active")
        for button, variant in (
            (self.btn_new_location, "primary"),
            (self.btn_edit_location, "secondary"),
            (self.btn_toggle_active, "secondary"),
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style(variant))
            action_row.addWidget(button)
        action_row.addStretch(1)
        actions_layout.addLayout(action_row)
        root.addWidget(actions)

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceLocationsControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | Active only | All criticalities")
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
        self.active_combo = QComboBox()
        self.active_combo.addItem("Active only", True)
        self.active_combo.addItem("Inactive only", False)
        self.active_combo.addItem("All statuses", None)
        self.criticality_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, name, type, status, or notes")
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Lifecycle"), 0, 2)
        filter_row.addWidget(self.active_combo, 0, 3)
        filter_row.addWidget(QLabel("Criticality"), 1, 0)
        filter_row.addWidget(self.criticality_combo, 1, 1)
        filter_row.addWidget(QLabel("Search"), 1, 2)
        filter_row.addWidget(self.search_edit, 1, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Locations", "-", "Visible in current scope", CFG.COLOR_ACCENT)
        self.active_card = KpiCard("Active", "-", "Ready for operational use", CFG.COLOR_SUCCESS)
        self.parented_card = KpiCard("Child Locations", "-", "Nested under a parent location", CFG.COLOR_WARNING)
        for card in (self.total_card, self.active_card, self.parented_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        panel, layout = build_admin_surface_card(
            object_name="maintenanceLocationsGridSurface",
            alt=False,
        )
        title = QLabel("Location Library")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Maintenance-owned location records used by assets, systems, planning, and work execution.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.selection_summary = QLabel("Select a location to edit or toggle its active state.")
        self.selection_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.selection_summary.setWordWrap(True)
        layout.addWidget(self.selection_summary)
        self.table = build_admin_table(
            headers=("Code", "Name", "Site", "Parent", "Type", "Status", "Criticality", "Active"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.table)
        root.addWidget(panel, 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.active_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Locations", callback=self.reload_rows)
        )
        self.criticality_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Locations", callback=self.reload_rows)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Maintenance Locations", callback=self.reload_rows)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Locations", callback=self.reload_data)
        )
        self.btn_new_location.clicked.connect(
            make_guarded_slot(self, title="Maintenance Locations", callback=self.create_location)
        )
        self.btn_edit_location.clicked.connect(
            make_guarded_slot(self, title="Maintenance Locations", callback=self.edit_location)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Maintenance Locations", callback=self.toggle_active)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_location, self.btn_edit_location, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="maintenance.manage")
        self._sync_actions()

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_criticality = selected_combo_value(self.criticality_combo)
        try:
            sites = self._site_service.list_sites(active_only=None)
            all_locations = self._location_service.list_locations(active_only=None, site_id=selected_site_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Locations", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Locations", f"Failed to load maintenance locations: {exc}")
            return

        self._site_labels = {site.id: site.name for site in sites}
        self._all_locations = all_locations
        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{site.site_code} - {site.name}", site.id) for site in sites],
            selected_value=selected_site_id,
        )
        reset_combo_options(
            self.criticality_combo,
            placeholder="All criticalities",
            options=[(value.value.title(), value.value) for value in self._criticality_values(all_locations)],
            selected_value=selected_criticality,
        )
        self.reload_rows()

    def reload_rows(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_location_id = self._selected_location_id()
        try:
            rows = self._location_service.search_locations(
                search_text=self.search_edit.text(),
                active_only=self.active_combo.currentData(),
                site_id=selected_site_id,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Locations", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Locations", f"Failed to refresh maintenance locations: {exc}")
            return

        criticality = selected_combo_value(self.criticality_combo)
        if criticality:
            rows = [row for row in rows if row.criticality.value == criticality]
        self._rows = rows
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(rows)} locations")
        self.active_badge.setText(f"{sum(1 for row in rows if row.is_active)} active")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.active_combo.currentText()} | {self.criticality_combo.currentText()}"
            + (f" | Search: {self.search_edit.text().strip()}" if self.search_edit.text().strip() else "")
        )
        self.total_card.set_value(str(len(rows)))
        self.active_card.set_value(str(sum(1 for row in rows if row.is_active)))
        self.parented_card.set_value(str(sum(1 for row in rows if row.parent_location_id)))
        self._populate_table(selected_location_id=selected_location_id)

    def create_location(self) -> None:
        dialog = MaintenanceLocationEditDialog(
            site_options=self._site_options(),
            locations=self._all_locations,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._location_service.create_location(
                    site_id=dialog.site_id,
                    location_code=dialog.location_code,
                    name=dialog.name,
                    parent_location_id=dialog.parent_location_id,
                    location_type=dialog.location_type,
                    criticality=dialog.criticality,
                    status=dialog.status,
                    description=dialog.description,
                    notes=dialog.notes,
                    is_active=dialog.is_active,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Maintenance Locations", str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Maintenance Locations", f"Failed to create maintenance location: {exc}")
                return
            break
        self.reload_data()

    def edit_location(self) -> None:
        location = self._selected_location()
        if location is None:
            QMessageBox.information(self, "Maintenance Locations", "Select a location to edit.")
            return
        dialog = MaintenanceLocationEditDialog(
            site_options=self._site_options(),
            locations=self._all_locations,
            location=location,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._location_service.update_location(
                    location.id,
                    site_id=dialog.site_id,
                    location_code=dialog.location_code,
                    name=dialog.name,
                    parent_location_id=dialog.parent_location_id,
                    location_type=dialog.location_type,
                    criticality=dialog.criticality,
                    status=dialog.status,
                    description=dialog.description,
                    notes=dialog.notes,
                    is_active=dialog.is_active,
                    expected_version=location.version,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Maintenance Locations", str(exc))
                continue
            except ConcurrencyError as exc:
                QMessageBox.warning(self, "Maintenance Locations", str(exc))
                self.reload_data()
                return
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Maintenance Locations", f"Failed to update maintenance location: {exc}")
                return
            break
        self.reload_data()

    def toggle_active(self) -> None:
        location = self._selected_location()
        if location is None:
            QMessageBox.information(self, "Maintenance Locations", "Select a location to update.")
            return
        try:
            self._location_service.update_location(
                location.id,
                is_active=not location.is_active,
                expected_version=location.version,
            )
        except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Maintenance Locations", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Locations", f"Failed to update maintenance location: {exc}")
            return
        self.reload_data()

    def _populate_table(self, *, selected_location_id: str | None) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        parent_map = {row.id: row for row in self._all_locations}
        for row_index, row in enumerate(self._rows):
            parent = parent_map.get(row.parent_location_id or "")
            values = (
                row.location_code,
                row.name,
                self._site_labels.get(row.site_id, row.site_id),
                f"{parent.location_code} - {parent.name}" if parent is not None else "-",
                row.location_type or "-",
                row.status.value.title(),
                row.criticality.value.title(),
                "Yes" if row.is_active else "No",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.table.setItem(row_index, column, item)
            if selected_location_id and row.id == selected_location_id:
                selected_row = row_index
        self.table.blockSignals(False)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
        self._sync_actions()

    def _selected_location_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_location(self):
        location_id = self._selected_location_id()
        if not location_id:
            return None
        return next((row for row in self._rows if row.id == location_id), None)

    def _site_options(self) -> list[tuple[str, str]]:
        return [(f"{site.site_code} - {site.name}", site.id) for site in self._site_service.list_sites(active_only=None)]

    @staticmethod
    def _criticality_values(rows) -> list:
        values = {row.criticality for row in rows}
        return sorted(values, key=lambda value: value.value)

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

    def _sync_actions(self) -> None:
        location = self._selected_location()
        has_location = location is not None
        if location is None:
            self.selection_summary.setText("Select a location to edit or toggle its active state.")
        else:
            self.selection_summary.setText(
                f"Selected: {location.location_code} | Site: {self._site_labels.get(location.site_id, location.site_id)} | Status: {location.status.value.title()}"
            )
        self.btn_new_location.setEnabled(self._can_manage)
        self.btn_edit_location.setEnabled(self._can_manage and has_location)
        self.btn_toggle_active.setEnabled(self._can_manage and has_location)

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


__all__ = ["MaintenanceLocationsTab"]
