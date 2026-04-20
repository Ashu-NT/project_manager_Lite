from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class RegisterEntryDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        entry: RegisterEntry | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Register Entry")
        self.resize(620, 560)

        self.type_combo = QComboBox()
        self.severity_combo = QComboBox()
        self.status_combo = QComboBox()
        for value in RegisterEntryType:
            self.type_combo.addItem(value.value.title(), userData=value)
        for value in RegisterEntrySeverity:
            self.severity_combo.addItem(value.value.title(), userData=value)
        for value in RegisterEntryStatus:
            self.status_combo.addItem(value.value.replace("_", " ").title(), userData=value)

        self.title_edit = QLineEdit()
        self.owner_edit = QLineEdit()
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat(CFG.DATE_FORMAT)
        self.no_due_date = QCheckBox("No due date")
        self.description_edit = QTextEdit()
        self.impact_edit = QTextEdit()
        self.response_edit = QTextEdit()
        for editor in (self.description_edit, self.impact_edit, self.response_edit):
            editor.setMinimumHeight(90)

        current_due = entry.due_date if entry is not None and entry.due_date is not None else date.today()
        self.due_date_edit.setDate(QDate(current_due.year, current_due.month, current_due.day))
        self.no_due_date.toggled.connect(self.due_date_edit.setDisabled)

        form = QFormLayout()
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.addRow("Type", self.type_combo)
        form.addRow("Title", self.title_edit)
        form.addRow("Severity", self.severity_combo)
        form.addRow("Status", self.status_combo)
        form.addRow("Owner", self.owner_edit)
        form.addRow("Due date", self.due_date_edit)
        form.addRow("", self.no_due_date)
        form.addRow("Description", self.description_edit)
        form.addRow("Impact", self.impact_edit)
        form.addRow("Response", self.response_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

        self._load_entry(entry)

    def _load_entry(self, entry: RegisterEntry | None) -> None:
        if entry is None:
            self.no_due_date.setChecked(True)
            return
        self._set_combo_value(self.type_combo, entry.entry_type)
        self._set_combo_value(self.severity_combo, entry.severity)
        self._set_combo_value(self.status_combo, entry.status)
        self.title_edit.setText(entry.title)
        self.owner_edit.setText(entry.owner_name or "")
        self.no_due_date.setChecked(entry.due_date is None)
        self.description_edit.setPlainText(entry.description or "")
        self.impact_edit.setPlainText(entry.impact_summary or "")
        self.response_edit.setPlainText(entry.response_plan or "")

    @staticmethod
    def _set_combo_value(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    @property
    def entry_type(self) -> RegisterEntryType:
        return as_register_entry_type(self.type_combo.currentData() or self.type_combo.currentText())

    @property
    def title(self) -> str:
        return self.title_edit.text().strip()

    @property
    def severity(self) -> RegisterEntrySeverity:
        return as_register_entry_severity(self.severity_combo.currentData() or self.severity_combo.currentText())

    @property
    def status(self) -> RegisterEntryStatus:
        return as_register_entry_status(self.status_combo.currentData() or self.status_combo.currentText())

    @property
    def owner_name(self) -> str | None:
        return self.owner_edit.text().strip() or None

    @property
    def due_date(self) -> date | None:
        if self.no_due_date.isChecked():
            return None
        value = self.due_date_edit.date()
        return date(value.year(), value.month(), value.day())

    @property
    def description(self) -> str:
        return self.description_edit.toPlainText().strip()

    @property
    def impact_summary(self) -> str:
        return self.impact_edit.toPlainText().strip()

    @property
    def response_plan(self) -> str:
        return self.response_edit.toPlainText().strip()


__all__ = ["RegisterEntryDialog"]
