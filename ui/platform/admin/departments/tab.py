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

from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.org.domain import Department
from core.platform.notifications.domain_events import domain_events
from core.platform.org import DepartmentService, SiteService
from ui.platform.admin.departments.dialogs import DepartmentEditDialog
from ui.platform.admin.shared_header import build_admin_header
from ui.platform.admin.shared_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class DepartmentAdminTab(QWidget):
    def __init__(
        self,
        department_service: DepartmentService,
        site_service: SiteService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._department_service = department_service
        self._site_service = site_service
        self._user_session = user_session
        self._can_manage_departments = has_permission(self._user_session, "settings.manage")
        self._rows: list[Department] = []
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
            context = self._department_service.get_context_organization()
            self._rows = self._department_service.list_departments()
            self._site_lookup = self._load_site_lookup()
            self._location_lookup = self._load_location_lookup()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Departments", str(exc))
            context_label = "-"
            self._rows = []
            self._site_lookup = {}
            self._location_lookup = {}
        except Exception as exc:
            QMessageBox.critical(self, "Departments", f"Failed to load departments: {exc}")
            context_label = "-"
            self._rows = []
            self._site_lookup = {}
            self._location_lookup = {}
        else:
            context_label = context.display_name
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
                self._department_service.create_department(
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
            except ValidationError as exc:
                QMessageBox.warning(self, "Departments", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Departments", f"Failed to create department: {exc}")
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
                self._department_service.update_department(
                    department.id,
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
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Departments", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_departments()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Departments", f"Failed to update department: {exc}")
                return
            break
        self.reload_departments()

    def toggle_active(self) -> None:
        department = self._selected_department()
        if department is None:
            QMessageBox.information(self, "Departments", "Please select a department.")
            return
        try:
            self._department_service.update_department(
                department.id,
                is_active=not department.is_active,
                expected_version=department.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Departments", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Departments", f"Failed to update department: {exc}")
            return
        self.reload_departments()

    def _selected_department(self) -> Department | None:
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

    def _update_header_badges(self, rows: list[Department], *, context_label: str) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.department_context_badge.setText(f"Context: {context_label}")
        self.department_count_badge.setText(f"{len(rows)} departments")
        self.department_active_badge.setText(f"{active_count} active")

    def _available_sites(self):
        if self._site_service is None:
            return []
        try:
            return self._site_service.list_sites(active_only=True)
        except BusinessRuleError:
            return []

    def _load_site_lookup(self) -> dict[str, str]:
        return {site.id: site.site_code for site in self._available_sites()}

    def _available_locations(self):
        try:
            return self._department_service.list_available_location_references(active_only=True)
        except BusinessRuleError:
            return []

    def _load_location_lookup(self) -> dict[str, str]:
        return {
            row.id: f"{row.location_code} - {row.name}"
            for row in self._available_locations()
        }

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
