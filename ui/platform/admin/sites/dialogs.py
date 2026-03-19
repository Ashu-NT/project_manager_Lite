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

from core.platform.common.models import Site
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class SiteEditDialog(QDialog):
    def __init__(self, parent=None, site: Site | None = None):
        super().__init__(parent)
        self.setWindowTitle("Site" + (" - Edit" if site else " - New"))

        self.site_code_edit = QLineEdit()
        self.display_name_edit = QLineEdit()
        for edit in (self.site_code_edit, self.display_name_edit):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if site is not None:
            self.site_code_edit.setText(site.site_code)
            self.display_name_edit.setText(site.display_name)
            self.active_check.setChecked(site.is_active)
        else:
            self.active_check.setChecked(True)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Site code:", self.site_code_edit)
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
        if not self.site_code:
            QMessageBox.warning(self, "Site", "Site code is required.")
            return
        if not self.display_name:
            QMessageBox.warning(self, "Site", "Site name is required.")
            return
        self.accept()

    @property
    def site_code(self) -> str:
        return self.site_code_edit.text().strip().upper()

    @property
    def display_name(self) -> str:
        return self.display_name_edit.text().strip()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()


__all__ = ["SiteEditDialog"]
