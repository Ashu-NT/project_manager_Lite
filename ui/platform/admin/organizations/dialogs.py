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

from core.platform.common.models import Organization
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class OrganizationEditDialog(QDialog):
    def __init__(self, parent=None, organization: Organization | None = None):
        super().__init__(parent)
        self.setWindowTitle("Organization" + (" - Edit" if organization else " - New"))

        self.organization_code_edit = QLineEdit()
        self.display_name_edit = QLineEdit()
        self.timezone_edit = QLineEdit()
        self.base_currency_edit = QLineEdit()
        for edit in (
            self.organization_code_edit,
            self.display_name_edit,
            self.timezone_edit,
            self.base_currency_edit,
        ):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.active_check = QCheckBox("Active organization")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if organization is not None:
            self.organization_code_edit.setText(organization.organization_code)
            self.display_name_edit.setText(organization.display_name)
            self.timezone_edit.setText(organization.timezone_name)
            self.base_currency_edit.setText(organization.base_currency)
            self.active_check.setChecked(organization.is_active)
        else:
            self.timezone_edit.setText("UTC")
            self.base_currency_edit.setText("EUR")
            self.active_check.setChecked(True)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Organization code:", self.organization_code_edit)
        form.addRow("Display name:", self.display_name_edit)
        form.addRow("Timezone:", self.timezone_edit)
        form.addRow("Base currency:", self.base_currency_edit)
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
        if not self.organization_code:
            QMessageBox.warning(self, "Organization", "Organization code is required.")
            return
        if not self.display_name:
            QMessageBox.warning(self, "Organization", "Organization name is required.")
            return
        if not self.timezone_name:
            QMessageBox.warning(self, "Organization", "Timezone is required.")
            return
        if not self.base_currency:
            QMessageBox.warning(self, "Organization", "Base currency is required.")
            return
        self.accept()

    @property
    def organization_code(self) -> str:
        return self.organization_code_edit.text().strip().upper()

    @property
    def display_name(self) -> str:
        return self.display_name_edit.text().strip()

    @property
    def timezone_name(self) -> str:
        return self.timezone_edit.text().strip()

    @property
    def base_currency(self) -> str:
        return self.base_currency_edit.text().strip().upper()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()


__all__ = ["OrganizationEditDialog"]
