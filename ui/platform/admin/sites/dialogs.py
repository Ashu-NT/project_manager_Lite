from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from core.platform.org.domain import Site
from ui.platform.shared.code_generation import CodeFieldWidget
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class SiteEditDialog(QDialog):
    def __init__(self, parent=None, site: Site | None = None):
        super().__init__(parent)
        self.setWindowTitle("Site" + (" - Edit" if site else " - New"))

        self.site_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.site_code_field = CodeFieldWidget(
            prefix="SITE",
            line_edit=self.site_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.city_edit = QLineEdit()
        self.country_edit = QLineEdit()
        self.timezone_edit = QLineEdit()
        self.currency_code_edit = QLineEdit()
        self.site_type_edit = QLineEdit()
        self.status_edit = QLineEdit()
        self.description_edit = QLineEdit()
        for edit in (
            self.site_code_edit,
            self.name_edit,
            self.city_edit,
            self.country_edit,
            self.timezone_edit,
            self.currency_code_edit,
            self.site_type_edit,
            self.status_edit,
            self.description_edit,
        ):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(90)
        self.notes_edit.setPlaceholderText("Optional site notes, operating context, or rollout details.")

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if site is not None:
            self.site_code_edit.setText(site.site_code)
            self.name_edit.setText(site.name)
            self.city_edit.setText(site.city)
            self.country_edit.setText(site.country)
            self.timezone_edit.setText(site.timezone)
            self.currency_code_edit.setText(site.currency_code)
            self.site_type_edit.setText(site.site_type)
            self.status_edit.setText(site.status)
            self.description_edit.setText(site.description)
            self.notes_edit.setPlainText(site.notes or "")
            self.active_check.setChecked(site.is_active)
        else:
            self.status_edit.setText("ACTIVE")
            self.active_check.setChecked(True)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Site code:", self.site_code_field)
        form.addRow("Name:", self.name_edit)
        form.addRow("City:", self.city_edit)
        form.addRow("Country:", self.country_edit)
        form.addRow("Timezone:", self.timezone_edit)
        form.addRow("Currency:", self.currency_code_edit)
        form.addRow("Site type:", self.site_type_edit)
        form.addRow("Status:", self.status_edit)
        form.addRow("Description:", self.description_edit)
        form.addRow("Notes:", self.notes_edit)
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
        if not self.site_code:
            QMessageBox.warning(self, "Site", "Site code is required.")
            return
        if not self.name:
            QMessageBox.warning(self, "Site", "Site name is required.")
            return
        self.accept()

    @property
    def site_code(self) -> str:
        return self.site_code_edit.text().strip().upper()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def city(self) -> str:
        return self.city_edit.text().strip()

    @property
    def country(self) -> str:
        return self.country_edit.text().strip()

    @property
    def timezone_name(self) -> str:
        return self.timezone_edit.text().strip()

    @property
    def currency_code(self) -> str:
        return self.currency_code_edit.text().strip().upper()

    @property
    def site_type(self) -> str:
        return self.site_type_edit.text().strip()

    @property
    def status(self) -> str:
        return self.status_edit.text().strip().upper()

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()


__all__ = ["SiteEditDialog"]
