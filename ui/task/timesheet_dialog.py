from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.models import TaskAssignment, TimeEntry
from core.services.task import TaskService
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class TimeEntryEditDialog(QDialog):
    def __init__(self, parent=None, *, entry: TimeEntry | None = None):
        super().__init__(parent)
        self.setWindowTitle("Time Entry")

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        default_date = entry.entry_date if entry is not None else date.today()
        self.date_edit.setDate(QDate(default_date.year, default_date.month, default_date.day))

        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0.25, 24.0)
        self.hours_spin.setDecimals(2)
        self.hours_spin.setSingleStep(0.25)
        self.hours_spin.setValue(float(entry.hours if entry is not None else 1.0))

        self.note_input = QTextEdit()
        self.note_input.setMinimumHeight(100)
        self.note_input.setPlaceholderText("What work was done?")
        self.note_input.setPlainText(entry.note if entry is not None else "")

        form = QFormLayout()
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.addRow("Date", self.date_edit)
        form.addRow("Hours", self.hours_spin)
        form.addRow("Note", self.note_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def entry_date(self) -> date:
        value = self.date_edit.date()
        return date(value.year(), value.month(), value.day())

    @property
    def hours(self) -> float:
        return float(self.hours_spin.value())

    @property
    def note(self) -> str:
        return self.note_input.toPlainText().strip()


class TimesheetDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        task_service: TaskService,
        assignment: TaskAssignment,
        task_name: str,
        resource_name: str,
    ) -> None:
        super().__init__(parent)
        self._task_service = task_service
        self._assignment = assignment
        self._task_name = task_name
        self._resource_name = resource_name
        self.setWindowTitle(f"Timesheet - {resource_name}")
        self.resize(760, 480)

        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_SM)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel(f"Task: {task_name} | Resource: {resource_name}")
        title.setStyleSheet(CFG.INFO_TEXT_STYLE)
        title.setWordWrap(True)
        root.addWidget(title)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        root.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Hours", "User", "Note"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        root.addWidget(self.table, 1)

        row = QHBoxLayout()
        self.btn_add = QPushButton("Add Entry")
        self.btn_edit = QPushButton("Edit Entry")
        self.btn_delete = QPushButton("Delete Entry")
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for btn in (self.btn_add, self.btn_edit, self.btn_delete, self.btn_close):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            row.addWidget(btn)
        row.addStretch()
        root.addLayout(row)

        self.btn_add.clicked.connect(self._add_entry)
        self.btn_edit.clicked.connect(self._edit_entry)
        self.btn_delete.clicked.connect(self._delete_entry)
        self.btn_close.clicked.connect(self.accept)

        self.reload_entries()

    def reload_entries(self) -> None:
        entries = self._task_service.list_time_entries_for_assignment(self._assignment.id)
        self.table.setRowCount(len(entries))
        total = 0.0
        for row, entry in enumerate(entries):
            total += float(entry.hours or 0.0)
            date_item = QTableWidgetItem(str(entry.entry_date))
            date_item.setData(Qt.UserRole, entry.id)
            hours_item = QTableWidgetItem(f"{float(entry.hours or 0.0):.2f}")
            hours_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, hours_item)
            self.table.setItem(row, 2, QTableWidgetItem(entry.author_username or "unknown"))
            self.table.setItem(row, 3, QTableWidgetItem(entry.note or ""))
        self.summary_label.setText(f"Entries: {len(entries)} | Total hours: {total:.2f}")
        self.btn_edit.setEnabled(bool(entries))
        self.btn_delete.setEnabled(bool(entries))

    def _selected_entry_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item is not None else None

    def _add_entry(self) -> None:
        dlg = TimeEntryEditDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            self._task_service.add_time_entry(
                self._assignment.id,
                entry_date=dlg.entry_date,
                hours=dlg.hours,
                note=dlg.note,
            )
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()

    def _edit_entry(self) -> None:
        entry_id = self._selected_entry_id()
        if not entry_id:
            QMessageBox.information(self, "Timesheet", "Please select an entry.")
            return
        entry = next(
            (item for item in self._task_service.list_time_entries_for_assignment(self._assignment.id) if item.id == entry_id),
            None,
        )
        if entry is None:
            QMessageBox.warning(self, "Timesheet", "Selected entry no longer exists.")
            self.reload_entries()
            return
        dlg = TimeEntryEditDialog(self, entry=entry)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            self._task_service.update_time_entry(
                entry.id,
                entry_date=dlg.entry_date,
                hours=dlg.hours,
                note=dlg.note,
            )
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()

    def _delete_entry(self) -> None:
        entry_id = self._selected_entry_id()
        if not entry_id:
            QMessageBox.information(self, "Timesheet", "Please select an entry.")
            return
        confirm = QMessageBox.question(self, "Timesheet", "Delete selected time entry?")
        if confirm != QMessageBox.Yes:
            return
        try:
            self._task_service.delete_time_entry(entry_id)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()


__all__ = ["TimeEntryEditDialog", "TimesheetDialog"]
