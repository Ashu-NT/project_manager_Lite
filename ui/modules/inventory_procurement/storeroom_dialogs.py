from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from core.modules.inventory_procurement.domain import Storeroom


_STOREROOM_STATUSES = ("DRAFT", "ACTIVE", "INACTIVE", "CLOSED")


class StoreroomEditDialog(QDialog):
    def __init__(
        self,
        *,
        storeroom: Storeroom | None = None,
        site_options: list[tuple[str, str]] | None = None,
        manager_options: list[tuple[str, str]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._storeroom = storeroom
        self._site_options = list(site_options or [])
        self._manager_options = list(manager_options or [])
        self.setWindowTitle("Edit Storeroom" if storeroom is not None else "New Storeroom")
        self.resize(540, 540)
        self._setup_ui()
        self._load_storeroom()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Storerooms stay tied to shared sites while inventory keeps the operational controls and stock-handling rules."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.storeroom_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.site_combo = QComboBox()
        for label, site_id in self._site_options:
            self.site_combo.addItem(label, site_id)
        self.status_combo = QComboBox()
        self.status_combo.addItems(_STOREROOM_STATUSES)
        self.storeroom_type_edit = QLineEdit()
        self.currency_code_edit = QLineEdit()
        self.manager_party_combo = QComboBox()
        for label, party_id in self._manager_options:
            self.manager_party_combo.addItem(label, party_id)
        self.allows_issue_check = QCheckBox("Issue")
        self.allows_transfer_check = QCheckBox("Transfer")
        self.allows_receiving_check = QCheckBox("Receiving")
        self.internal_supplier_check = QCheckBox("Internal supplier")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Operational rules, usage notes, or stocking guidance.")

        form.addRow("Storeroom Code", self.storeroom_code_edit)
        form.addRow("Name", self.name_edit)
        form.addRow("Site", self.site_combo)
        form.addRow("Status", self.status_combo)
        form.addRow("Storeroom Type", self.storeroom_type_edit)
        form.addRow("Currency", self.currency_code_edit)
        form.addRow("Manager Party", self.manager_party_combo)

        control_row = QHBoxLayout()
        control_row.addWidget(self.allows_issue_check)
        control_row.addWidget(self.allows_transfer_check)
        control_row.addWidget(self.allows_receiving_check)
        control_row.addWidget(self.internal_supplier_check)
        control_row.addStretch(1)
        form.addRow("Controls", control_row)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_storeroom(self) -> None:
        storeroom = self._storeroom
        if storeroom is None:
            self.status_combo.setCurrentText("DRAFT")
            self.allows_issue_check.setChecked(True)
            self.allows_transfer_check.setChecked(True)
            self.allows_receiving_check.setChecked(True)
            return
        self.storeroom_code_edit.setText(storeroom.storeroom_code)
        self.name_edit.setText(storeroom.name)
        self.status_combo.setCurrentText(storeroom.status)
        self.storeroom_type_edit.setText(storeroom.storeroom_type)
        self.currency_code_edit.setText(storeroom.default_currency_code)
        self._set_combo_to_data(self.site_combo, storeroom.site_id)
        self._set_combo_to_data(self.manager_party_combo, storeroom.manager_party_id or "")
        self.allows_issue_check.setChecked(storeroom.allows_issue)
        self.allows_transfer_check.setChecked(storeroom.allows_transfer)
        self.allows_receiving_check.setChecked(storeroom.allows_receiving)
        self.internal_supplier_check.setChecked(storeroom.is_internal_supplier)
        self.notes_edit.setPlainText(storeroom.notes)

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def storeroom_code(self) -> str:
        return self.storeroom_code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def site_id(self) -> str:
        return str(self.site_combo.currentData() or "").strip()

    @property
    def status(self) -> str:
        return str(self.status_combo.currentText()).strip().upper()

    @property
    def storeroom_type(self) -> str:
        return self.storeroom_type_edit.text().strip()

    @property
    def default_currency_code(self) -> str:
        return self.currency_code_edit.text().strip()

    @property
    def manager_party_id(self) -> str | None:
        value = str(self.manager_party_combo.currentData() or "").strip()
        return value or None

    @property
    def allows_issue(self) -> bool:
        return self.allows_issue_check.isChecked()

    @property
    def allows_transfer(self) -> bool:
        return self.allows_transfer_check.isChecked()

    @property
    def allows_receiving(self) -> bool:
        return self.allows_receiving_check.isChecked()

    @property
    def is_internal_supplier(self) -> bool:
        return self.internal_supplier_check.isChecked()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


__all__ = ["StoreroomEditDialog"]
