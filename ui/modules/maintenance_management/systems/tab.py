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
from core.modules.maintenance_management import MaintenanceLocationService, MaintenanceSystemService
from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org import SiteService
from ui.modules.maintenance_management.shared import (
    build_maintenance_header,
    make_accent_badge,
    make_filter_toggle_button,
    make_meta_badge,
    reset_combo_options,
    selected_combo_value,
    set_filter_panel_visible,
)
from ui.modules.maintenance_management.systems.dialogs import MaintenanceSystemEditDialog
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.modules.project_management.dashboard.widgets import KpiCard
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class MaintenanceSystemsTab(QWidget):
    def __init__(
        self,
        *,
        system_service: MaintenanceSystemService,
        location_service: MaintenanceLocationService,
        site_service: SiteService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._system_service = system_service
        self._location_service = location_service
        self._site_service = site_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(user_session, "maintenance.manage")
        self._rows = []
        self._all_systems = []
        self._all_locations = []
        self._site_labels: dict[str, str] = {}
        self._location_labels: dict[str, str] = {}
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
        self.count_badge = make_meta_badge("0 systems")
        self.active_badge = make_meta_badge("0 active")
        self.access_badge = make_meta_badge("Manage Enabled" if self._can_manage else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenanceSystemsHeaderCard",
            eyebrow_text="MAINTENANCE LIBRARIES",
            title_text="Systems",
            subtitle_text="Manage maintenance system hierarchy records that group process, utility, and equipment structure beneath site and location context.",
            badges=(self.context_badge, self.count_badge, self.active_badge, self.access_badge),
        )

        actions, actions_layout = build_admin_surface_card(
            object_name="maintenanceSystemsActionSurface",
            alt=False,
        )
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_new_system = QPushButton("New System")
        self.btn_edit_system = QPushButton("Edit System")
        self.btn_toggle_active = QPushButton("Toggle Active")
        for button, variant in (
            (self.btn_new_system, "primary"),
            (self.btn_edit_system, "secondary"),
            (self.btn_toggle_active, "secondary"),
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style(variant))
            action_row.addWidget(button)
        action_row.addStretch(1)
        actions_layout.addLayout(action_row)
        root.addWidget(actions)

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceSystemsControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All locations | Active only | All criticalities")
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
        self.location_combo = QComboBox()
        self.active_combo = QComboBox()
        self.active_combo.addItem("Active only", True)
        self.active_combo.addItem("Inactive only", False)
        self.active_combo.addItem("All statuses", None)
        self.criticality_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, name, type, status, or notes")
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Location"), 0, 2)
        filter_row.addWidget(self.location_combo, 0, 3)
        filter_row.addWidget(QLabel("Lifecycle"), 1, 0)
        filter_row.addWidget(self.active_combo, 1, 1)
        filter_row.addWidget(QLabel("Criticality"), 1, 2)
        filter_row.addWidget(self.criticality_combo, 1, 3)
        filter_row.addWidget(QLabel("Search"), 2, 0)
        filter_row.addWidget(self.search_edit, 2, 1, 1, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Systems", "-", "Visible in current scope", CFG.COLOR_ACCENT)
        self.active_card = KpiCard("Active", "-", "Ready for planning and execution", CFG.COLOR_SUCCESS)
        self.parented_card = KpiCard("Child Systems", "-", "Nested under a parent system", CFG.COLOR_WARNING)
        for card in (self.total_card, self.active_card, self.parented_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        panel, layout = build_admin_surface_card(
            object_name="maintenanceSystemsGridSurface",
            alt=False,
        )
        title = QLabel("System Library")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Maintenance system records used for hierarchy, planning scope, and work-order routing.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.selection_summary = QLabel("Select a system to edit or toggle its active state.")
        self.selection_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.selection_summary.setWordWrap(True)
        layout.addWidget(self.selection_summary)
        self.table = build_admin_table(
            headers=("Code", "Name", "Site", "Location", "Parent", "Type", "Status", "Active"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.table)
        root.addWidget(panel, 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.location_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Systems", callback=self.reload_rows)
        )
        self.active_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Systems", callback=self.reload_rows)
        )
        self.criticality_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Systems", callback=self.reload_rows)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Maintenance Systems", callback=self.reload_rows)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Systems", callback=self.reload_data)
        )
        self.btn_new_system.clicked.connect(
            make_guarded_slot(self, title="Maintenance Systems", callback=self.create_system)
        )
        self.btn_edit_system.clicked.connect(
            make_guarded_slot(self, title="Maintenance Systems", callback=self.edit_system)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Maintenance Systems", callback=self.toggle_active)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_system, self.btn_edit_system, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="maintenance.manage")
        self._sync_actions()

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_location_id = selected_combo_value(self.location_combo)
        selected_criticality = selected_combo_value(self.criticality_combo)
        try:
            sites = self._site_service.list_sites(active_only=None)
            self._all_locations = self._location_service.list_locations(active_only=None, site_id=selected_site_id)
            self._all_systems = self._system_service.list_systems(active_only=None, site_id=selected_site_id, location_id=selected_location_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Systems", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Systems", f"Failed to load maintenance systems: {exc}")
            return

        self._site_labels = {site.id: site.name for site in sites}
        self._location_labels = {location.id: location.name for location in self._all_locations}
        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{site.site_code} - {site.name}", site.id) for site in sites],
            selected_value=selected_site_id,
        )
        reset_combo_options(
            self.location_combo,
            placeholder="All locations",
            options=[(f"{location.location_code} - {location.name}", location.id) for location in self._all_locations],
            selected_value=selected_location_id,
        )
        reset_combo_options(
            self.criticality_combo,
            placeholder="All criticalities",
            options=[(value.value.title(), value.value) for value in self._criticality_values(self._all_systems)],
            selected_value=selected_criticality,
        )
        self.reload_rows()

    def reload_rows(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_system_id = self._selected_system_id()
        try:
            rows = self._system_service.search_systems(
                search_text=self.search_edit.text(),
                active_only=self.active_combo.currentData(),
                site_id=selected_site_id,
                location_id=selected_combo_value(self.location_combo),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Systems", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Systems", f"Failed to refresh maintenance systems: {exc}")
            return

        criticality = selected_combo_value(self.criticality_combo)
        if criticality:
            rows = [row for row in rows if row.criticality.value == criticality]
        self._rows = rows
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(rows)} systems")
        self.active_badge.setText(f"{sum(1 for row in rows if row.is_active)} active")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.location_combo.currentText()} | {self.active_combo.currentText()} | {self.criticality_combo.currentText()}"
            + (f" | Search: {self.search_edit.text().strip()}" if self.search_edit.text().strip() else "")
        )
        self.total_card.set_value(str(len(rows)))
        self.active_card.set_value(str(sum(1 for row in rows if row.is_active)))
        self.parented_card.set_value(str(sum(1 for row in rows if row.parent_system_id)))
        self._populate_table(selected_system_id=selected_system_id)

    def create_system(self) -> None:
        dialog = MaintenanceSystemEditDialog(
            site_options=self._site_options(),
            locations=self._all_locations,
            systems=self._all_systems,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._system_service.create_system(
                    site_id=dialog.site_id,
                    system_code=dialog.system_code,
                    name=dialog.name,
                    location_id=dialog.location_id,
                    parent_system_id=dialog.parent_system_id,
                    system_type=dialog.system_type,
                    criticality=dialog.criticality,
                    status=dialog.status,
                    description=dialog.description,
                    notes=dialog.notes,
                    is_active=dialog.is_active,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Maintenance Systems", str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Maintenance Systems", f"Failed to create maintenance system: {exc}")
                return
            break
        self.reload_data()

    def edit_system(self) -> None:
        system = self._selected_system()
        if system is None:
            QMessageBox.information(self, "Maintenance Systems", "Select a system to edit.")
            return
        dialog = MaintenanceSystemEditDialog(
            site_options=self._site_options(),
            locations=self._all_locations,
            systems=self._all_systems,
            system=system,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._system_service.update_system(
                    system.id,
                    site_id=dialog.site_id,
                    system_code=dialog.system_code,
                    name=dialog.name,
                    location_id=dialog.location_id,
                    parent_system_id=dialog.parent_system_id,
                    system_type=dialog.system_type,
                    criticality=dialog.criticality,
                    status=dialog.status,
                    description=dialog.description,
                    notes=dialog.notes,
                    is_active=dialog.is_active,
                    expected_version=system.version,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Maintenance Systems", str(exc))
                continue
            except ConcurrencyError as exc:
                QMessageBox.warning(self, "Maintenance Systems", str(exc))
                self.reload_data()
                return
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Maintenance Systems", f"Failed to update maintenance system: {exc}")
                return
            break
        self.reload_data()

    def toggle_active(self) -> None:
        system = self._selected_system()
        if system is None:
            QMessageBox.information(self, "Maintenance Systems", "Select a system to update.")
            return
        try:
            self._system_service.update_system(
                system.id,
                is_active=not system.is_active,
                expected_version=system.version,
            )
        except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Maintenance Systems", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Systems", f"Failed to update maintenance system: {exc}")
            return
        self.reload_data()

    def _populate_table(self, *, selected_system_id: str | None) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        parent_map = {row.id: row for row in self._all_systems}
        for row_index, row in enumerate(self._rows):
            parent = parent_map.get(row.parent_system_id or "")
            values = (
                row.system_code,
                row.name,
                self._site_labels.get(row.site_id, row.site_id),
                self._location_labels.get(row.location_id or "", row.location_id or "-"),
                f"{parent.system_code} - {parent.name}" if parent is not None else "-",
                row.system_type or "-",
                row.status.value.title(),
                "Yes" if row.is_active else "No",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.table.setItem(row_index, column, item)
            if selected_system_id and row.id == selected_system_id:
                selected_row = row_index
        self.table.blockSignals(False)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
        self._sync_actions()

    def _selected_system_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_system(self):
        system_id = self._selected_system_id()
        if not system_id:
            return None
        return next((row for row in self._rows if row.id == system_id), None)

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
        system = self._selected_system()
        has_system = system is not None
        if system is None:
            self.selection_summary.setText("Select a system to edit or toggle its active state.")
        else:
            self.selection_summary.setText(
                f"Selected: {system.system_code} | Location: {self._location_labels.get(system.location_id or '', system.location_id or '-')} | Status: {system.status.value.title()}"
            )
        self.btn_new_system.setEnabled(self._can_manage)
        self.btn_edit_system.setEnabled(self._can_manage and has_system)
        self.btn_toggle_active.setEnabled(self._can_manage and has_system)

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


__all__ = ["MaintenanceSystemsTab"]
