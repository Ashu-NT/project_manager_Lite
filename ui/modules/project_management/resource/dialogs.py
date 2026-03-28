from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.modules.project_management.domain.enums import CostType, WorkerType
from core.modules.project_management.domain.resource import Resource
from core.platform.org import EmployeeService
from ui.modules.project_management.resource.employee_context import employee_option_label, format_employee_context_from_record
from ui.platform.shared.styles.ui_config import UIConfig as CFG, CurrencyType


class ResourceEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        resource: Resource | None = None,
        employee_service: EmployeeService | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Resource" + (" - Edit" if resource else " - New"))
        self._resource: Resource | None = resource
        self._employee_service = employee_service
        self._employees: list[object] = []

        self.name_edit = QLineEdit()
        self.role_edit = QLineEdit()
        self.address_edit = QLineEdit()
        self.contact_edit = QLineEdit()
        for edit in (self.name_edit, self.role_edit, self.address_edit, self.contact_edit):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.rate_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.rate_spin.setMinimum(CFG.MONEY_MIN)
        self.rate_spin.setMaximum(CFG.MONEY_MAX)
        self.rate_spin.setDecimals(CFG.MONEY_DECIMALS)
        self.rate_spin.setSingleStep(CFG.MONEY_STEP)
        self.rate_spin.setAlignment(CFG.ALIGN_RIGHT)

        self.capacity_spin = QDoubleSpinBox()
        self.capacity_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.capacity_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.capacity_spin.setMinimum(1.0)
        self.capacity_spin.setMaximum(500.0)
        self.capacity_spin.setDecimals(1)
        self.capacity_spin.setSingleStep(5.0)
        self.capacity_spin.setAlignment(CFG.ALIGN_RIGHT)

        self.category_combo = QComboBox()
        self._cost_types: list[CostType] = [
            CostType.LABOR,
            CostType.MATERIAL,
            CostType.OVERHEAD,
            CostType.EQUIPMENT,
            CostType.CONTINGENCY,
            CostType.SUBCONTRACT,
            CostType.OTHER,
        ]
        for ct in self._cost_types:
            self.category_combo.addItem(ct.value, userData=ct)
        self.category_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.category_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.currency_combo = QComboBox()
        self.currency_combo.setEditable(True)
        for cur in CurrencyType:
            self.currency_combo.addItem(cur.value)
        self.currency_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.currency_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.worker_type_combo = QComboBox()
        self.worker_type_combo.addItem("Employee", userData=WorkerType.EMPLOYEE)
        self.worker_type_combo.addItem("External Worker", userData=WorkerType.EXTERNAL)
        self.worker_type_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.worker_type_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.employee_combo = QComboBox()
        self.employee_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.employee_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.employee_combo.addItem("Select employee", userData=None)
        self._load_employees()
        self.employee_context_value = QLabel("-")
        self.employee_context_value.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        self.employee_context_value.setWordWrap(True)

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if resource is not None:
            worker_type = getattr(resource, "worker_type", WorkerType.EXTERNAL)
            self.worker_type_combo.setCurrentIndex(0 if worker_type == WorkerType.EMPLOYEE else 1)
            self.name_edit.setText(resource.name)
            self.role_edit.setText(resource.role or "")
            if resource.hourly_rate is not None:
                self.rate_spin.setValue(resource.hourly_rate)
            self.capacity_spin.setValue(float(getattr(resource, "capacity_percent", 100.0) or 100.0))
            self.address_edit.setText(getattr(resource, "address", "") or "")
            self.contact_edit.setText(getattr(resource, "contact", "") or "")
            for i, ct in enumerate(self._cost_types):
                if ct == getattr(resource, "cost_type", CostType.LABOR):
                    self.category_combo.setCurrentIndex(i)
                    break
            if getattr(resource, "currency_code", None):
                self.currency_combo.setCurrentText(resource.currency_code)
            self.active_check.setChecked(getattr(resource, "is_active", True))
            if getattr(resource, "employee_id", None):
                idx = self.employee_combo.findData(resource.employee_id)
                if idx >= 0:
                    self.employee_combo.setCurrentIndex(idx)
        else:
            self.worker_type_combo.setCurrentIndex(1)
            self.capacity_spin.setValue(100.0)
            self.currency_combo.setCurrentText(CFG.DEFAULT_CURRENCY_CODE)
            self.active_check.setChecked(True)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form.addRow("Worker type:", self.worker_type_combo)
        form.addRow("Employee:", self.employee_combo)
        form.addRow("Shared context:", self.employee_context_value)
        form.addRow("Name:", self.name_edit)
        form.addRow("Role:", self.role_edit)
        form.addRow("Category:", self.category_combo)
        form.addRow("Hourly rate:", self.rate_spin)
        form.addRow("Capacity (%):", self.capacity_spin)
        form.addRow("Currency:", self.currency_combo)
        form.addRow("Address:", self.address_edit)
        form.addRow("Contact:", self.contact_edit)
        form.addRow("", self.active_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        buttons.setCenterButtons(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setMinimumSize(self.sizeHint())

        self.worker_type_combo.currentIndexChanged.connect(self._sync_worker_mode)
        self.employee_combo.currentIndexChanged.connect(self._sync_worker_mode)
        self._sync_worker_mode()

    def _load_employees(self) -> None:
        if self._employee_service is None:
            self.employee_combo.setEnabled(False)
            return
        try:
            self._employees = self._employee_service.list_employees()
        except Exception:
            self._employees = []
            self.employee_combo.setEnabled(False)
            return
        for employee in self._employees:
            self.employee_combo.addItem(employee_option_label(employee), userData=employee.id)

    def _selected_employee(self):
        employee_id = self.employee_combo.currentData()
        for employee in self._employees:
            if employee.id == employee_id:
                return employee
        return None

    def _sync_worker_mode(self) -> None:
        is_employee = self.worker_type == WorkerType.EMPLOYEE
        self.employee_combo.setEnabled(is_employee and bool(self._employees))
        self.name_edit.setReadOnly(is_employee)
        self.role_edit.setReadOnly(is_employee)
        self.contact_edit.setReadOnly(is_employee)
        self.employee_context_value.setText("-")
        if is_employee:
            employee = self._selected_employee()
            if employee is not None:
                self.name_edit.setText(employee.full_name)
                self.role_edit.setText(employee.title or "")
                self.contact_edit.setText(employee.email or employee.phone or "")
                self.employee_context_value.setText(format_employee_context_from_record(employee))

    def _validate_and_accept(self) -> None:
        if self.worker_type == WorkerType.EMPLOYEE and not self.employee_id:
            QMessageBox.warning(self, "Resource", "Please select an employee.")
            return
        if self.worker_type == WorkerType.EXTERNAL and not self.name:
            QMessageBox.warning(self, "Resource", "Resource name is required.")
            return
        self.accept()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def role(self) -> str:
        return self.role_edit.text().strip()

    @property
    def hourly_rate(self) -> float:
        return self.rate_spin.value()

    @property
    def capacity_percent(self) -> float:
        return self.capacity_spin.value()

    @property
    def address(self) -> str:
        return self.address_edit.text().strip()

    @property
    def contact(self) -> str:
        return self.contact_edit.text().strip()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()

    @property
    def cost_type(self) -> CostType:
        idx = self.category_combo.currentIndex()
        if 0 <= idx < len(self._cost_types):
            return self._cost_types[idx]
        return CostType.LABOR

    @property
    def currency_code(self) -> str | None:
        txt = self.currency_combo.currentText().strip()
        return txt if txt else None

    @property
    def worker_type(self) -> WorkerType:
        return self.worker_type_combo.currentData() or WorkerType.EXTERNAL

    @property
    def employee_id(self) -> str | None:
        value = self.employee_combo.currentData()
        return str(value) if value else None


__all__ = ["ResourceEditDialog"]
