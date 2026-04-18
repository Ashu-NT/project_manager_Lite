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

from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.domain import Employee
from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.auth import UserSessionContext
from src.core.platform.org import DepartmentService, EmployeeService, SiteService
from src.ui.platform.dialogs.admin.employees.dialogs import EmployeeEditDialog
from src.ui.platform.widgets.admin_header import build_admin_header
from src.ui.platform.widgets.admin_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class EmployeeAdminTab(QWidget):
    def __init__(
        self,
        employee_service: EmployeeService,
        site_service: SiteService | None = None,
        department_service: DepartmentService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._employee_service = employee_service
        self._site_service = site_service
        self._department_service = department_service
        self._user_session = user_session
        self._can_manage_employees = has_permission(self._user_session, "employee.manage")
        self._can_manage_settings = has_permission(self._user_session, "settings.manage")
        self._rows: list[Employee] = []
        self._site_options: list[tuple[str, str]] = []
        self._department_options: list[tuple[str, str]] = []
        self._reference_status_text = "Shared refs: unavailable"
        self._setup_ui()
        self._reload_reference_options(show_feedback=False)
        self.reload_employees()
        domain_events.employees_changed.connect(self._on_employees_changed)
        domain_events.sites_changed.connect(self._on_reference_catalog_changed)
        domain_events.departments_changed.connect(self._on_reference_catalog_changed)
        domain_events.organizations_changed.connect(self._on_reference_catalog_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        access_label = "Manage Enabled" if self._can_manage_employees else "Read Only"
        build_admin_header(
            self,
            layout,
            object_name="employeeAdminHeaderCard",
            eyebrow_text="PEOPLE",
            title_text="Employee Directory",
            subtitle_text="Manage internal employees for staffing, planning, and future HR and payroll workflows.",
            badge_specs=(
                ("employee_scope_badge", "Internal Workforce", "accent"),
                ("employee_count_badge", "0 employees", "meta"),
                ("employee_active_badge", "0 active", "meta"),
                ("employee_reference_badge", self._reference_status_text, "meta"),
                ("employee_access_badge", access_label, "meta"),
            ),
        )

        build_admin_toolbar_surface(
            self,
            layout,
            object_name="employeeAdminControlSurface",
            button_specs=(
                ToolbarButtonSpec("btn_new_employee", "New Employee", "primary"),
                ToolbarButtonSpec("btn_edit_employee", "Edit Employee"),
                ToolbarButtonSpec("btn_toggle_active", "Toggle Active"),
                ToolbarButtonSpec("btn_open_sites", "Open Sites"),
                ToolbarButtonSpec("btn_open_departments", "Open Departments"),
                ToolbarButtonSpec("btn_refresh", CFG.REFRESH_BUTTON_LABEL),
            ),
        )

        self.table = build_admin_table(
            headers=("Code", "Full Name", "Department", "Site", "Title", "Type", "Contact", "Active"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
                QHeaderView.ResizeToContents,
            ),
        )
        layout.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Employees", callback=self.reload_employees))
        self.btn_new_employee.clicked.connect(
            make_guarded_slot(self, title="Employees", callback=self.create_employee)
        )
        self.btn_edit_employee.clicked.connect(
            make_guarded_slot(self, title="Employees", callback=self.edit_employee)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Employees", callback=self.toggle_active)
        )
        self.btn_open_sites.clicked.connect(
            make_guarded_slot(self, title="Employees", callback=self._open_sites_workspace)
        )
        self.btn_open_departments.clicked.connect(
            make_guarded_slot(self, title="Employees", callback=self._open_departments_workspace)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        apply_permission_hint(
            self.btn_new_employee,
            allowed=self._can_manage_employees,
            missing_permission="employee.manage",
        )
        apply_permission_hint(
            self.btn_edit_employee,
            allowed=self._can_manage_employees,
            missing_permission="employee.manage",
        )
        apply_permission_hint(
            self.btn_toggle_active,
            allowed=self._can_manage_employees,
            missing_permission="employee.manage",
        )
        apply_permission_hint(
            self.btn_open_sites,
            allowed=self._can_manage_settings,
            missing_permission="settings.manage",
        )
        apply_permission_hint(
            self.btn_open_departments,
            allowed=self._can_manage_settings,
            missing_permission="settings.manage",
        )
        self._sync_actions()

    def reload_employees(self) -> None:
        try:
            self._rows = self._employee_service.list_employees()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Employees", str(exc))
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Employees", f"Failed to load employees: {exc}")
            self._rows = []
        self.table.setRowCount(len(self._rows))
        for row, employee in enumerate(self._rows):
            contact = employee.email or employee.phone or "-"
            values = (
                employee.employee_code,
                employee.full_name,
                employee.department or "",
                getattr(employee, "site_name", "") or "",
                employee.title or "",
                employee.employment_type.value.replace("_", " ").title(),
                contact,
                "Yes" if employee.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 7:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, employee.id)
        self.table.clearSelection()
        self._update_header_badges(self._rows)
        self._sync_actions()

    def create_employee(self) -> None:
        self._reload_reference_options(show_feedback=False)
        dlg = EmployeeEditDialog(
            parent=self,
            department_options=self._department_options,
            site_options=self._site_options,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._employee_service.create_employee(
                    employee_code=dlg.employee_code,
                    full_name=dlg.full_name,
                    department_id=dlg.department_id,
                    department=dlg.department,
                    site_id=dlg.site_id,
                    site_name=dlg.site_name,
                    title=dlg.title,
                    employment_type=dlg.employment_type,
                    email=dlg.email,
                    phone=dlg.phone,
                    is_active=dlg.is_active,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Employees", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Employees", f"Failed to create employee: {exc}")
                return
            break
        self.reload_employees()

    def edit_employee(self) -> None:
        employee = self._selected_employee()
        if employee is None:
            QMessageBox.information(self, "Employees", "Please select an employee.")
            return
        self._reload_reference_options(show_feedback=False)
        dlg = EmployeeEditDialog(
            parent=self,
            employee=employee,
            department_options=self._department_options,
            site_options=self._site_options,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._employee_service.update_employee(
                    employee.id,
                    employee_code=dlg.employee_code,
                    full_name=dlg.full_name,
                    department_id=dlg.department_id,
                    department=dlg.department,
                    site_id=dlg.site_id,
                    site_name=dlg.site_name,
                    title=dlg.title,
                    employment_type=dlg.employment_type,
                    email=dlg.email,
                    phone=dlg.phone,
                    is_active=dlg.is_active,
                    expected_version=employee.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Employees", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_employees()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Employees", f"Failed to update employee: {exc}")
                return
            break
        self.reload_employees()

    def toggle_active(self) -> None:
        employee = self._selected_employee()
        if employee is None:
            QMessageBox.information(self, "Employees", "Please select an employee.")
            return
        try:
            self._employee_service.update_employee(
                employee.id,
                is_active=not employee.is_active,
                expected_version=employee.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Employees", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Employees", f"Failed to update employee: {exc}")
            return
        self.reload_employees()

    def _selected_employee(self) -> Employee | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        employee_id = item.data(Qt.UserRole)
        for employee in self._rows:
            if employee.id == employee_id:
                return employee
        return None

    def _on_employees_changed(self, _employee_id: str) -> None:
        self.reload_employees()

    def _on_reference_catalog_changed(self, _entity_id: str) -> None:
        self._reload_reference_options(show_feedback=False)

    def _sync_actions(self) -> None:
        has_employee = self._selected_employee() is not None
        self.btn_new_employee.setEnabled(self._can_manage_employees)
        self.btn_edit_employee.setEnabled(self._can_manage_employees and has_employee)
        self.btn_toggle_active.setEnabled(self._can_manage_employees and has_employee)
        self.btn_open_sites.setEnabled(self._can_manage_settings)
        self.btn_open_departments.setEnabled(self._can_manage_settings)

    def _update_header_badges(self, rows: list[Employee]) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.employee_count_badge.setText(f"{len(rows)} employees")
        self.employee_active_badge.setText(f"{active_count} active")
        self.employee_reference_badge.setText(self._reference_status_text)

    def _reload_reference_options(self, *, show_feedback: bool) -> None:
        self._site_options = self._load_site_options(show_feedback=show_feedback)
        self._department_options = self._load_department_options(show_feedback=show_feedback)
        if self._site_service is None and self._department_service is None:
            self._reference_status_text = "Shared refs: unavailable"
        elif not self._can_manage_settings and not self._site_options and not self._department_options:
            self._reference_status_text = "Shared refs: limited access"
        else:
            self._reference_status_text = (
                f"Shared refs: {len(self._site_options)} sites / {len(self._department_options)} departments"
            )
        if hasattr(self, "employee_reference_badge"):
            self.employee_reference_badge.setText(self._reference_status_text)

    def _load_site_options(self, *, show_feedback: bool) -> list[tuple[str, str]]:
        if self._site_service is None:
            return []
        try:
            return [(site.name, site.id) for site in self._site_service.list_sites(active_only=True)]
        except BusinessRuleError:
            return []
        except Exception as exc:
            if show_feedback:
                QMessageBox.warning(self, "Employees", f"Unable to load shared sites: {exc}")
            return []

    def _load_department_options(self, *, show_feedback: bool) -> list[tuple[str, str]]:
        if self._department_service is None:
            return []
        try:
            return [(department.name, department.id) for department in self._department_service.list_departments(active_only=True)]
        except BusinessRuleError:
            return []
        except Exception as exc:
            if show_feedback:
                QMessageBox.warning(self, "Employees", f"Unable to load shared departments: {exc}")
            return []

    def _open_sites_workspace(self) -> None:
        self._open_workspace("Sites")

    def _open_departments_workspace(self) -> None:
        self._open_workspace("Departments")

    def _open_workspace(self, label: str) -> None:
        main_window = self.window()
        if main_window is not None and hasattr(main_window, "focus_workspace") and main_window.focus_workspace(label):
            return
        QMessageBox.information(
            self,
            "Employees",
            f"The {label} workspace is not available in the current shell context.",
        )


__all__ = ["EmployeeAdminTab"]
