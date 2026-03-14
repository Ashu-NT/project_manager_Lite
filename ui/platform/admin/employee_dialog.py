from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.platform.common.models import Employee, EmploymentType
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class EmployeeEditDialog(QDialog):
    def __init__(self, parent=None, employee: Employee | None = None):
        super().__init__(parent)
        self.setWindowTitle("Employee" + (" - Edit" if employee else " - New"))

        self.employee_code_edit = QLineEdit()
        self.full_name_edit = QLineEdit()
        self.department_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        for edit in (
            self.employee_code_edit,
            self.full_name_edit,
            self.department_edit,
            self.title_edit,
            self.email_edit,
            self.phone_edit,
        ):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.employment_type_combo = QComboBox()
        for employment_type in EmploymentType:
            self.employment_type_combo.addItem(employment_type.value.replace("_", " ").title(), userData=employment_type)
        self.employment_type_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.employment_type_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if employee is not None:
            self.employee_code_edit.setText(employee.employee_code)
            self.full_name_edit.setText(employee.full_name)
            self.department_edit.setText(employee.department or "")
            self.title_edit.setText(employee.title or "")
            self.email_edit.setText(employee.email or "")
            self.phone_edit.setText(employee.phone or "")
            for index in range(self.employment_type_combo.count()):
                if self.employment_type_combo.itemData(index) == employee.employment_type:
                    self.employment_type_combo.setCurrentIndex(index)
                    break
            self.active_check.setChecked(employee.is_active)
        else:
            self.active_check.setChecked(True)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Employee code:", self.employee_code_edit)
        form.addRow("Full name:", self.full_name_edit)
        form.addRow("Department:", self.department_edit)
        form.addRow("Title:", self.title_edit)
        form.addRow("Employment type:", self.employment_type_combo)
        form.addRow("Email:", self.email_edit)
        form.addRow("Phone:", self.phone_edit)
        form.addRow("", self.active_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setMinimumSize(self.sizeHint())

    def _validate_and_accept(self) -> None:
        if not self.employee_code:
            QMessageBox.warning(self, "Employee", "Employee code is required.")
            return
        if not self.full_name:
            QMessageBox.warning(self, "Employee", "Employee name is required.")
            return
        self.accept()

    @property
    def employee_code(self) -> str:
        return self.employee_code_edit.text().strip().upper()

    @property
    def full_name(self) -> str:
        return self.full_name_edit.text().strip()

    @property
    def department(self) -> str:
        return self.department_edit.text().strip()

    @property
    def title(self) -> str:
        return self.title_edit.text().strip()

    @property
    def employment_type(self) -> EmploymentType:
        return self.employment_type_combo.currentData() or EmploymentType.FULL_TIME

    @property
    def email(self) -> str:
        return self.email_edit.text().strip().lower()

    @property
    def phone(self) -> str:
        return self.phone_edit.text().strip()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()


__all__ = ["EmployeeEditDialog"]
