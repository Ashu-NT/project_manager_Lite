from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.platform.org.domain import Employee, EmploymentType
from ui.platform.shared.styles.ui_config import UIConfig as CFG


def _current_reference_id(combo: QComboBox) -> str | None:
    current_text = combo.currentText().strip()
    for index in range(combo.count()):
        if combo.itemText(index).strip() != current_text:
            continue
        value = str(combo.itemData(index) or "").strip()
        return value or None
    return None


def _populate_reference_combo(
    combo: QComboBox,
    *,
    options: list[tuple[str, str]] | list[str],
    current_id: str | None = None,
    current_value: str = "",
    placeholder: str,
) -> None:
    combo.clear()
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)
    combo.addItem("", userData=None)
    seen: set[str] = set()
    by_id: dict[str, int] = {}
    for option in options:
        if isinstance(option, tuple):
            value, option_id = option
        else:
            value, option_id = option, ""
        normalized = (value or "").strip()
        normalized_id = (option_id or "").strip()
        if not normalized or normalized in seen:
            continue
        combo.addItem(normalized, userData=normalized_id or None)
        by_id[normalized_id] = combo.count() - 1
        seen.add(normalized)
    normalized_current = (current_value or "").strip()
    if normalized_current and normalized_current not in seen:
        combo.addItem(normalized_current, userData=None)
    normalized_current_id = (current_id or "").strip()
    index = by_id.get(normalized_current_id, -1)
    if index < 0:
        index = combo.findText(normalized_current, Qt.MatchFixedString)
    if index >= 0:
        combo.setCurrentIndex(index)
    else:
        combo.setEditText(normalized_current)
    line_edit = combo.lineEdit()
    if line_edit is not None:
        line_edit.setPlaceholderText(placeholder)


class EmployeeEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        employee: Employee | None = None,
        *,
        department_options: list[tuple[str, str]] | None = None,
        site_options: list[tuple[str, str]] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Employee" + (" - Edit" if employee else " - New"))

        self.employee_code_edit = QLineEdit()
        self.full_name_edit = QLineEdit()
        self.department_combo = QComboBox()
        self.site_name_combo = QComboBox()
        self.title_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        for edit in (
            self.employee_code_edit,
            self.full_name_edit,
            self.title_edit,
            self.email_edit,
            self.phone_edit,
        ):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        for combo in (self.department_combo, self.site_name_combo):
            combo.setSizePolicy(CFG.INPUT_POLICY)
            combo.setFixedHeight(CFG.INPUT_HEIGHT)
            combo.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

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

        _populate_reference_combo(
            self.department_combo,
            options=department_options or [],
            current_id=getattr(employee, "department_id", None) if employee is not None else None,
            current_value=employee.department if employee is not None else "",
            placeholder="Select or type a department",
        )
        _populate_reference_combo(
            self.site_name_combo,
            options=site_options or [],
            current_id=getattr(employee, "site_id", None) if employee is not None else None,
            current_value=getattr(employee, "site_name", "") if employee is not None else "",
            placeholder="Select or type a site",
        )

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Employee code:", self.employee_code_edit)
        form.addRow("Full name:", self.full_name_edit)
        form.addRow("Department:", self.department_combo)
        form.addRow("Site:", self.site_name_combo)
        form.addRow("Title:", self.title_edit)
        form.addRow("Employment type:", self.employment_type_combo)
        form.addRow("Email:", self.email_edit)
        form.addRow("Phone:", self.phone_edit)
        form.addRow("", self.active_check)

        reference_hint = QLabel(
            "Department and Site prefer the shared platform masters. If a legacy value is not there yet, you can still keep the readable text during the transition."
        )
        reference_hint.setWordWrap(True)
        reference_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addLayout(form)
        layout.addWidget(reference_hint)
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
        return self.department_combo.currentText().strip()

    @property
    def department_id(self) -> str | None:
        return _current_reference_id(self.department_combo)

    @property
    def site_name(self) -> str:
        return self.site_name_combo.currentText().strip()

    @property
    def site_id(self) -> str | None:
        return _current_reference_id(self.site_name_combo)

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
