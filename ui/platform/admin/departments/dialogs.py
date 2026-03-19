from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.platform.common.models import Department
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class DepartmentEditDialog(QDialog):
    def __init__(self, parent=None, department: Department | None = None):
        super().__init__(parent)
        self.setWindowTitle("Department" + (" - Edit" if department else " - New"))

        self.department_code_edit = QLineEdit()
        self.display_name_edit = QLineEdit()
        for edit in (self.department_code_edit, self.display_name_edit):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if department is not None:
            self.department_code_edit.setText(department.department_code)
            self.display_name_edit.setText(department.display_name)
            self.active_check.setChecked(department.is_active)
        else:
            self.active_check.setChecked(True)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Department code:", self.department_code_edit)
        form.addRow("Display name:", self.display_name_edit)
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
        if not self.department_code:
            QMessageBox.warning(self, "Department", "Department code is required.")
            return
        if not self.display_name:
            QMessageBox.warning(self, "Department", "Department name is required.")
            return
        self.accept()

    @property
    def department_code(self) -> str:
        return self.department_code_edit.text().strip().upper()

    @property
    def display_name(self) -> str:
        return self.display_name_edit.text().strip()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()


__all__ = ["DepartmentEditDialog"]
