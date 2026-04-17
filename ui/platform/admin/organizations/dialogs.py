from __future__ import annotations

from PySide6.QtWidgets import (
    QGroupBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.platform.org.domain import Organization
from src.core.platform.modules import EnterpriseModule
from ui.platform.shared.code_generation import CodeFieldWidget
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class OrganizationEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        organization: Organization | None = None,
        available_modules: list[EnterpriseModule] | tuple[EnterpriseModule, ...] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Organization" + (" - Edit" if organization else " - New"))
        self._available_modules = tuple(available_modules or ())
        self._module_checks: dict[str, QCheckBox] = {}
        self._create_mode = organization is None

        self.organization_code_edit = QLineEdit()
        self.display_name_edit = QLineEdit()
        self.organization_code_field = CodeFieldWidget(
            prefix="ORG",
            line_edit=self.organization_code_edit,
            hint_getters=(lambda: self.display_name_edit.text(),),
        )
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
        form.addRow("Organization code:", self.organization_code_field)
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
        if self._create_mode and self._available_modules:
            layout.addWidget(self._build_initial_modules_section())
        layout.addWidget(buttons)
        self.setMinimumSize(self.sizeHint())

    def _build_initial_modules_section(self) -> QGroupBox:
        section = QGroupBox("Initial Modules")
        section_layout = QVBoxLayout(section)
        section_layout.setSpacing(CFG.SPACING_XS)
        hint = QLabel("Choose which business modules should be licensed and enabled when this organization is created.")
        hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        hint.setWordWrap(True)
        section_layout.addWidget(hint)
        for module in self._available_modules:
            checkbox = QCheckBox(module.label)
            checkbox.setChecked(module.default_enabled and module.stage != "planned")
            checkbox.setEnabled(module.stage != "planned")
            if module.stage == "planned":
                checkbox.setText(f"{module.label} (Planned)")
            if module.description:
                checkbox.setToolTip(module.description)
            section_layout.addWidget(checkbox)
            self._module_checks[module.code] = checkbox
        return section

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

    @property
    def initial_module_codes(self) -> list[str]:
        return [
            module_code
            for module_code, checkbox in self._module_checks.items()
            if checkbox.isChecked() and checkbox.isEnabled()
        ]


__all__ = ["OrganizationEditDialog"]
