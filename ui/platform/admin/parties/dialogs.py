from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from src.core.platform.party import Party, PartyType
from ui.platform.shared.code_generation import CodeFieldWidget
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class PartyEditDialog(QDialog):
    def __init__(self, parent=None, party: Party | None = None):
        super().__init__(parent)
        self.setWindowTitle("Party" + (" - Edit" if party else " - New"))

        self.party_code_edit = QLineEdit()
        self.party_name_edit = QLineEdit()
        self.party_code_field = CodeFieldWidget(
            prefix="PARTY",
            line_edit=self.party_code_edit,
            hint_getters=(lambda: self.party_name_edit.text(),),
        )
        self.legal_name_edit = QLineEdit()
        self.contact_name_edit = QLineEdit()
        self.country_edit = QLineEdit()
        self.city_edit = QLineEdit()
        for edit in (
            self.party_code_edit,
            self.party_name_edit,
            self.legal_name_edit,
            self.contact_name_edit,
            self.country_edit,
            self.city_edit,
        ):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.party_type_combo = QComboBox()
        for party_type in PartyType:
            self.party_type_combo.addItem(party_type.value.replace("_", " ").title(), userData=party_type)
        self.party_type_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.party_type_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(90)
        self.notes_edit.setPlaceholderText("Optional notes about supplier scope, manufacturer status, or service role.")

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if party is not None:
            self.party_code_edit.setText(party.party_code)
            self.party_name_edit.setText(party.party_name)
            self.legal_name_edit.setText(party.legal_name)
            self.contact_name_edit.setText(party.contact_name)
            self.country_edit.setText(party.country)
            self.city_edit.setText(party.city)
            self.notes_edit.setPlainText(party.notes or "")
            self.active_check.setChecked(party.is_active)
            self._select_combo(self.party_type_combo, party.party_type)
        else:
            self.active_check.setChecked(True)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Party code:", self.party_code_field)
        form.addRow("Name:", self.party_name_edit)
        form.addRow("Party type:", self.party_type_combo)
        form.addRow("Legal name:", self.legal_name_edit)
        form.addRow("Contact name:", self.contact_name_edit)
        form.addRow("Country:", self.country_edit)
        form.addRow("City:", self.city_edit)
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

    def _select_combo(self, combo: QComboBox, value) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                break

    def _validate_and_accept(self) -> None:
        if not self.party_code:
            QMessageBox.warning(self, "Party", "Party code is required.")
            return
        if not self.party_name:
            QMessageBox.warning(self, "Party", "Party name is required.")
            return
        self.accept()

    @property
    def party_code(self) -> str:
        return self.party_code_edit.text().strip().upper()

    @property
    def party_name(self) -> str:
        return self.party_name_edit.text().strip()

    @property
    def party_type(self) -> PartyType:
        return self.party_type_combo.currentData() or PartyType.GENERAL

    @property
    def legal_name(self) -> str:
        return self.legal_name_edit.text().strip()

    @property
    def contact_name(self) -> str:
        return self.contact_name_edit.text().strip()

    @property
    def country(self) -> str:
        return self.country_edit.text().strip()

    @property
    def city(self) -> str:
        return self.city_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()


__all__ = ["PartyEditDialog"]
