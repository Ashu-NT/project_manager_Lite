from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.api.desktop.platform import (
    DepartmentCreateCommand,
    DepartmentDto,
    DepartmentLocationReferenceDto,
    DepartmentUpdateCommand,
    DesktopApiError,
    PlatformDepartmentDesktopApi,
    PlatformSiteDesktopApi,
    SiteDto,
)
from src.core.platform.auth import UserSessionContext
from src.core.platform.notifications.domain_events import domain_events
from src.ui.platform.dialogs.admin.departments.dialogs import DepartmentEditDialog
from src.ui.platform.widgets.admin_header import build_admin_header
from src.ui.platform.widgets.admin_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class DepartmentAdminTab(QWidget):
    def __init__(
        self,
        *,
        platform_department_api: PlatformDepartmentDesktopApi,
        platform_site_api: PlatformSiteDesktopApi,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._platform_department_api = platform_department_api
        self._platform_site_api = platform_site_api
        self._user_session = user_session
        self._can_manage_departments = has_permission(self._user_session, "settings.manage")
        self._rows: list[DepartmentDto] = []
        self._sites: list[SiteDto] = []
        self._locations: list[DepartmentLocationReferenceDto] = []
        self._site_lookup: dict[str, str] = {}
        self._location_lookup: dict[str, str] = {}
        self._setup_ui()
        self.reload_departments()
        domain_events.departments_changed.connect(self._on_departments_changed)
        domain_events.sites_changed.connect(self._on_sites_changed)
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        access_label = "Manage Enabled" if self._can_manage_departments else "Read Only"
        build_admin_header(
            self,
            layout,
            object_name="departmentAdminHeaderCard",
            eyebrow_text="DEPARTMENT MASTER",
            title_text="Departments",
            subtitle_text="Manage shared department records for workforce context, reporting consistency, and future HR alignment.",
            badge_specs=(
                ("department_context_badge", "Context: -", "accent"),
                ("department_count_badge", "0 departments", "meta"),
                ("department_active_badge", "0 active", "meta"),
                ("department_access_badge", access_label, "meta"),
            ),
        )

        build_admin_toolbar_surface(
            self,
            layout,
            object_name="departmentAdminControlSurface",
            button_specs=(
                ToolbarButtonSpec("btn_new_department", "New Department", "primary"),
                ToolbarButtonSpec("btn_edit_department", "Edit Department"),
                ToolbarButtonSpec("btn_toggle_active", "Toggle Active"),
                ToolbarButtonSpec("btn_refresh", CFG.REFRESH_BUTTON_LABEL),
            ),
        )

        self.table = build_admin_table(
            headers=("Code", "Name", "Site", "Default Location", "Type", "Active"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
            ),
        )
        layout.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Departments", callback=self.reload_departments)
        )
        self.btn_new_department.clicked.connect(
            make_guarded_slot(self, title="Departments", callback=self.create_department)
        )
        self.btn_edit_department.clicked.connect(
            make_guarded_slot(self, title="Departments", callback=self.edit_department)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Departments", callback=self.toggle_active)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_department, self.btn_edit_department, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage_departments, missing_permission="settings.manage")
        self._sync_actions()

    def reload_departments(self) -> None:
        try:
            context_result = self._platform_department_api.get_context()
            departments_result = self._platform_department_api.list_departments()
            sites_result = self._platform_site_api.list_sites(active_only=True)
            locations_result = self._platform_department_api.list_location_references(active_only=True)
        except Exception as exc:
            QMessageBox.critical(self, "Departments", f"Failed to load departments: {exc}")
            context_label = "-"
            self._rows = []
            self._sites = []
            self._locations = []
            self._site_lookup = {}
            self._location_lookup = {}
        else:
            context_label = context_result.data.display_name if context_result.ok and context_result.data else "-"
            if not context_result.ok:
                self._show_api_error(context_result.error)
            self._rows = list(departments_result.data or ()) if departments_result.ok else []
            self._sites = list(sites_result.data or ()) if sites_result.ok else []
            self._locations = list(locations_result.data or ()) if locations_result.ok else []
            for result in (departments_result, sites_result, locations_result):
                if not result.ok:
                    self._show_api_error(result.error)
            self._site_lookup = self._load_site_lookup()
            self._location_lookup = self._load_location_lookup()
        self.table.setRowCount(len(self._rows))
        for row, department in enumerate(self._rows):
            values = (
                department.department_code,
                department.name,
                self._site_lookup.get(department.site_id or "", "-"),
                self._location_lookup.get(department.default_location_id or "", "-"),
                department.department_type or "-",
                "Yes" if department.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 5:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, department.id)
        self.table.clearSelection()
        self._update_header_badges(self._rows, context_label=context_label)
        self._sync_actions()

    def create_department(self) -> None:
        dlg = DepartmentEditDialog(
            parent=self,
            sites=self._available_sites(),
            parent_departments=self._rows,
            location_options=self._available_locations(),
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                error = self._create_department_from_dialog(dlg)
            except Exception as exc:
                QMessageBox.critical(self, "Departments", f"Failed to create department: {exc}")
                return
            if error is not None:
                self._show_api_error(error)
                if error.category in {"validation", "conflict"}:
                    continue
                return
            break
        self.reload_departments()

    def edit_department(self) -> None:
        department = self._selected_department()
        if department is None:
            QMessageBox.information(self, "Departments", "Please select a department.")
            return
        dlg = DepartmentEditDialog(
            parent=self,
            department=department,
            sites=self._available_sites(),
            parent_departments=self._rows,
            location_options=self._available_locations(),
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                error = self._update_department_from_dialog(department, dlg)
            except Exception as exc:
                QMessageBox.critical(self, "Departments", f"Failed to update department: {exc}")
                return
            if error is not None:
                self._show_api_error(error)
                if error.category == "conflict":
                    self.reload_departments()
                    return
                if error.category == "validation":
                    continue
                return
            break
        self.reload_departments()

    def toggle_active(self) -> None:
        department = self._selected_department()
        if department is None:
            QMessageBox.information(self, "Departments", "Please select a department.")
            return
        try:
            result = self._platform_department_api.update_department(
                DepartmentUpdateCommand(
                    department_id=department.id,
                    is_active=not department.is_active,
                    expected_version=department.version,
                )
            )
        except Exception as exc:
            QMessageBox.critical(self, "Departments", f"Failed to update department: {exc}")
            return
        if not result.ok:
            self._show_api_error(result.error)
            return
        self.reload_departments()

    def _selected_department(self) -> DepartmentDto | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        department_id = item.data(Qt.UserRole)
        for department in self._rows:
            if department.id == department_id:
                return department
        return None

    def _update_header_badges(self, rows: list[DepartmentDto], *, context_label: str) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.department_context_badge.setText(f"Context: {context_label}")
        self.department_count_badge.setText(f"{len(rows)} departments")
        self.department_active_badge.setText(f"{active_count} active")

    def _available_sites(self) -> list[SiteDto]:
        return self._sites

    def _load_site_lookup(self) -> dict[str, str]:
        return {site.id: site.site_code for site in self._available_sites()}

    def _available_locations(self) -> list[DepartmentLocationReferenceDto]:
        return self._locations

    def _load_location_lookup(self) -> dict[str, str]:
        return {
            row.id: f"{row.location_code} - {row.name}"
            for row in self._available_locations()
        }

    def _create_department_from_dialog(self, dlg: DepartmentEditDialog) -> DesktopApiError | None:
        result = self._platform_department_api.create_department(
            DepartmentCreateCommand(
                department_code=dlg.department_code,
                name=dlg.name,
                description=dlg.description,
                site_id=dlg.site_id,
                default_location_id=dlg.default_location_id,
                parent_department_id=dlg.parent_department_id,
                department_type=dlg.department_type,
                cost_center_code=dlg.cost_center_code,
                notes=dlg.notes,
                is_active=dlg.is_active,
            )
        )
        return None if result.ok else result.error

    def _update_department_from_dialog(
        self,
        department: DepartmentDto,
        dlg: DepartmentEditDialog,
    ) -> DesktopApiError | None:
        result = self._platform_department_api.update_department(
            DepartmentUpdateCommand(
                department_id=department.id,
                department_code=dlg.department_code,
                name=dlg.name,
                description=dlg.description,
                site_id=dlg.site_id,
                default_location_id=dlg.default_location_id,
                parent_department_id=dlg.parent_department_id,
                department_type=dlg.department_type,
                cost_center_code=dlg.cost_center_code,
                notes=dlg.notes,
                is_active=dlg.is_active,
                expected_version=department.version,
            )
        )
        return None if result.ok else result.error

    def _show_api_error(self, error: DesktopApiError | None) -> None:
        message = error.message if error is not None else "The platform department API did not return a result."
        QMessageBox.warning(self, "Departments", message)

    def _on_departments_changed(self, _department_id: str) -> None:
        self.reload_departments()

    def _on_sites_changed(self, _site_id: str) -> None:
        self.reload_departments()

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_departments()

    def _sync_actions(self) -> None:
        has_department = self._selected_department() is not None
        self.btn_new_department.setEnabled(self._can_manage_departments)
        self.btn_edit_department.setEnabled(self._can_manage_departments and has_department)
        self.btn_toggle_active.setEnabled(self._can_manage_departments and has_department)


__all__ = ["DepartmentAdminTab"]
