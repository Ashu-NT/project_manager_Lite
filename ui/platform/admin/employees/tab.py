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

from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.models import Employee
from core.platform.notifications.domain_events import domain_events
from core.platform.auth import UserSessionContext
from core.platform.org import EmployeeService
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.admin.employees.dialogs import EmployeeEditDialog
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class EmployeeAdminTab(QWidget):
    def __init__(
        self,
        employee_service: EmployeeService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._employee_service = employee_service
        self._user_session = user_session
        self._can_manage_employees = has_permission(self._user_session, "employee.manage")
        self._rows: list[Employee] = []
        self._setup_ui()
        self.reload_employees()
        domain_events.employees_changed.connect(self._on_employees_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("employeeAdminHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#employeeAdminHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)
        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("PEOPLE")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.addWidget(eyebrow)
        title = QLabel("Employee Directory")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.addWidget(title)
        subtitle = QLabel("Manage internal employees for staffing, planning, and future payroll workflows.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.employee_scope_badge = QLabel("Internal Workforce")
        self.employee_scope_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.employee_count_badge = QLabel("0 employees")
        self.employee_count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.employee_active_badge = QLabel("0 active")
        self.employee_active_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Manage Enabled" if self._can_manage_employees else "Read Only"
        self.employee_access_badge = QLabel(access_label)
        self.employee_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.employee_scope_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.employee_count_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.employee_active_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.employee_access_badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        controls = QWidget()
        controls.setObjectName("employeeAdminControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#employeeAdminControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)

        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_new_employee = QPushButton("New Employee")
        self.btn_edit_employee = QPushButton("Edit Employee")
        self.btn_toggle_active = QPushButton("Toggle Active")
        for btn in (
            self.btn_refresh,
            self.btn_new_employee,
            self.btn_edit_employee,
            self.btn_toggle_active,
        ):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new_employee.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit_employee.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_toggle_active.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        toolbar.addWidget(self.btn_new_employee)
        toolbar.addWidget(self.btn_edit_employee)
        toolbar.addWidget(self.btn_toggle_active)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar)
        layout.addWidget(controls)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Code", "Full Name", "Department", "Site", "Title", "Type", "Contact", "Active"]
        )
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header_widget = self.table.horizontalHeader()
        header_widget.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(1, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(6, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(7, QHeaderView.ResizeToContents)
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
        dlg = EmployeeEditDialog(parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._employee_service.create_employee(
                    employee_code=dlg.employee_code,
                    full_name=dlg.full_name,
                    department=dlg.department,
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
        dlg = EmployeeEditDialog(parent=self, employee=employee)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._employee_service.update_employee(
                    employee.id,
                    employee_code=dlg.employee_code,
                    full_name=dlg.full_name,
                    department=dlg.department,
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

    def _sync_actions(self) -> None:
        has_employee = self._selected_employee() is not None
        self.btn_new_employee.setEnabled(self._can_manage_employees)
        self.btn_edit_employee.setEnabled(self._can_manage_employees and has_employee)
        self.btn_toggle_active.setEnabled(self._can_manage_employees and has_employee)

    def _update_header_badges(self, rows: list[Employee]) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.employee_count_badge.setText(f"{len(rows)} employees")
        self.employee_active_badge.setText(f"{active_count} active")


__all__ = ["EmployeeAdminTab"]
