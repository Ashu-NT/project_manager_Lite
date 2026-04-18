from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidgetSelectionRange,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.modules.project_management.domain.task import TaskAssignment
from src.core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus
from src.core.platform.auth import UserSessionContext
from core.modules.project_management.services.task import TaskService
from core.modules.project_management.services.timesheet import TimesheetService
from ui.platform.shared.guards import has_permission
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


def _period_start(period_date: date) -> date:
    return period_date.replace(day=1)


class TimeEntryEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        entry: TimeEntry | None = None,
        default_date: date | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Time Entry")

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        initial_date = entry.entry_date if entry is not None else (default_date or date.today())
        self.date_edit.setDate(QDate(initial_date.year, initial_date.month, initial_date.day))

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
        timesheet_service: TimesheetService | TaskService,
        assignment: TaskAssignment,
        task_name: str,
        resource_name: str,
        user_session: UserSessionContext | None = None,
    ) -> None:
        super().__init__(parent)
        self._timesheet_service = timesheet_service
        self._assignment = assignment
        self._task_name = task_name
        self._resource_name = resource_name
        self._user_session = user_session
        self._can_manage_entries = has_permission(self._user_session, "task.manage")
        self._can_decide_period = has_permission(self._user_session, "timesheet.approve")
        self._can_lock_period = has_permission(self._user_session, "timesheet.lock")
        self.setWindowTitle(f"Timesheet - {resource_name}")
        self.resize(860, 560)

        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_SM)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel(f"Task: {task_name} | Resource: {resource_name}")
        title.setStyleSheet(CFG.INFO_TEXT_STYLE)
        title.setWordWrap(True)
        root.addWidget(title)

        period_row = QHBoxLayout()
        period_caption = QLabel("Period")
        period_caption.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        period_row.addWidget(period_caption)
        self.period_edit = QDateEdit()
        self.period_edit.setCalendarPopup(True)
        self.period_edit.setDisplayFormat("MMM yyyy")
        self.period_edit.setDate(self._default_period_qdate())
        self.period_edit.dateChanged.connect(lambda _value: self.reload_entries())
        period_row.addWidget(self.period_edit)
        period_row.addStretch()
        root.addLayout(period_row)

        self.period_badge = QLabel("OPEN")
        self.period_badge.setAlignment(Qt.AlignCenter)
        self.period_badge.setFixedHeight(CFG.INPUT_HEIGHT)
        root.addWidget(self.period_badge, 0, Qt.AlignLeft)

        self.period_status_label = QLabel("")
        self.period_status_label.setWordWrap(True)
        self.period_status_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        root.addWidget(self.period_status_label)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        root.addWidget(self.summary_label)

        self.scope_label = QLabel("")
        self.scope_label.setWordWrap(True)
        self.scope_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        root.addWidget(self.scope_label)

        self.period_queue_label = QLabel("")
        self.period_queue_label.setWordWrap(True)
        self.period_queue_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        root.addWidget(self.period_queue_label)

        self.period_table = QTableWidget(0, 5)
        self.period_table.setHorizontalHeaderLabels(["Period", "Status", "Hours", "Submitted", "Decided"])
        self.period_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.period_table.setSelectionMode(QTableWidget.SingleSelection)
        self.period_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.period_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.period_table)
        self.period_table.setMaximumHeight(190)
        self.period_table.itemSelectionChanged.connect(self._sync_period_picker_from_table)
        root.addWidget(self.period_table)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Hours", "User", "Note"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._sync_row_action_state)
        style_table(self.table)
        root.addWidget(self.table, 1)

        edit_row = QHBoxLayout()
        self.btn_add = QPushButton("Add Entry")
        self.btn_edit = QPushButton("Edit Entry")
        self.btn_delete = QPushButton("Delete Entry")
        for btn in (self.btn_add, self.btn_edit, self.btn_delete):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            edit_row.addWidget(btn)
        edit_row.addStretch()
        root.addLayout(edit_row)

        period_action_row = QHBoxLayout()
        self.btn_submit = QPushButton("Submit Period")
        self.btn_approve = QPushButton("Approve Period")
        self.btn_reject = QPushButton("Reject Period")
        self.btn_lock = QPushButton("Lock Period")
        self.btn_unlock = QPushButton("Unlock Period")
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for btn in (
            self.btn_submit,
            self.btn_approve,
            self.btn_reject,
            self.btn_lock,
            self.btn_unlock,
            self.btn_close,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            period_action_row.addWidget(btn)
        period_action_row.addStretch()
        root.addLayout(period_action_row)

        self.btn_add.clicked.connect(self._add_entry)
        self.btn_edit.clicked.connect(self._edit_entry)
        self.btn_delete.clicked.connect(self._delete_entry)
        self.btn_submit.clicked.connect(self._submit_period)
        self.btn_approve.clicked.connect(self._approve_period)
        self.btn_reject.clicked.connect(self._reject_period)
        self.btn_lock.clicked.connect(self._lock_period)
        self.btn_unlock.clicked.connect(self._unlock_period)
        self.btn_close.clicked.connect(self.accept)

        self.reload_entries()

    def _default_period_qdate(self) -> QDate:
        entries = self._timesheet_service.list_time_entries_for_assignment(self._assignment.id)
        target_date = max((entry.entry_date for entry in entries), default=date.today())
        target_date = _period_start(target_date)
        return QDate(target_date.year, target_date.month, target_date.day)

    def _current_period_start(self) -> date:
        value = self.period_edit.date()
        return _period_start(date(value.year(), value.month(), value.day()))

    def _period_assignment_entries(self) -> list[TimeEntry]:
        return self._timesheet_service.list_time_entries_for_assignment_period(
            self._assignment.id,
            period_start=self._current_period_start(),
        )

    def reload_entries(self) -> None:
        period_start = self._current_period_start()
        task_entries = self._period_assignment_entries()
        resource_entries = self._timesheet_service.list_time_entries_for_resource_period(
            self._assignment.resource_id,
            period_start=period_start,
        )
        period = self._timesheet_service.get_timesheet_period(
            self._assignment.resource_id,
            period_start=period_start,
        )

        self.table.setRowCount(len(task_entries))
        task_total = 0.0
        for row, entry in enumerate(task_entries):
            task_total += float(entry.hours or 0.0)
            date_item = QTableWidgetItem(str(entry.entry_date))
            date_item.setData(Qt.UserRole, entry.id)
            hours_item = QTableWidgetItem(f"{float(entry.hours or 0.0):.2f}")
            hours_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, hours_item)
            self.table.setItem(row, 2, QTableWidgetItem(entry.author_username or "unknown"))
            self.table.setItem(row, 3, QTableWidgetItem(entry.note or ""))

        resource_total = sum(float(entry.hours or 0.0) for entry in resource_entries)
        self.summary_label.setText(
            f"Task period entries: {len(task_entries)} | Task hours: {task_total:.2f}"
        )
        self.scope_label.setText(
            "Submitting or locking a period affects the full resource month. "
            f"Resource period total: {resource_total:.2f} hours across {len(resource_entries)} entries."
        )
        self.period_status_label.setText(self._format_period_status(period))
        self._update_period_badge(period)
        self._update_period_review_table(current_period=period_start)
        self._sync_period_action_state(
            period=period,
            has_task_entries=bool(task_entries),
            has_resource_entries=bool(resource_entries),
        )
        self._sync_row_action_state()

    def _format_period_status(self, period: TimesheetPeriod | None) -> str:
        period_start = self._current_period_start()
        base = f"Period {period_start.strftime('%B %Y')} status: "
        if period is None:
            return base + "OPEN"
        details = [period.status.value]
        if period.submitted_by_username and period.submitted_at is not None:
            details.append(f"submitted by {period.submitted_by_username}")
        if period.decided_by_username and period.decided_at is not None:
            details.append(f"decided by {period.decided_by_username}")
        if period.locked_at is not None and period.status == TimesheetPeriodStatus.LOCKED:
            details.append("locked")
        if period.decision_note:
            details.append(f"note: {period.decision_note}")
        return base + " | ".join(details)

    def _update_period_badge(self, period: TimesheetPeriod | None) -> None:
        status = (period.status if period is not None else TimesheetPeriodStatus.OPEN).value
        self.period_badge.setText(status.replace("_", " "))
        color = CFG.COLOR_ACCENT
        if status == TimesheetPeriodStatus.SUBMITTED.value:
            color = CFG.COLOR_WARNING
        elif status == TimesheetPeriodStatus.APPROVED.value:
            color = CFG.COLOR_SUCCESS
        elif status == TimesheetPeriodStatus.REJECTED.value:
            color = CFG.COLOR_DANGER
        elif status == TimesheetPeriodStatus.LOCKED.value:
            color = CFG.COLOR_TEXT_MUTED
        self.period_badge.setStyleSheet(
            f"border: 1px solid {color}; border-radius: 12px; padding: 2px 10px; font-weight: 700; color: {color};"
        )

    def _update_period_review_table(self, *, current_period: date) -> None:
        known_periods = {
            period.period_start: period
            for period in self._timesheet_service.list_timesheet_periods_for_resource(self._assignment.resource_id)
        }
        current_entries = self._timesheet_service.list_time_entries_for_assignment(self._assignment.id)
        for entry in current_entries:
            known_periods.setdefault(_period_start(entry.entry_date), None)
        ordered = sorted(known_periods.keys(), reverse=True)
        self.period_table.setRowCount(len(ordered))
        submitted_count = 0
        for row_idx, period_start in enumerate(ordered):
            period = known_periods[period_start]
            entries = self._timesheet_service.list_time_entries_for_resource_period(
                self._assignment.resource_id,
                period_start=period_start,
            )
            if period is not None and period.status == TimesheetPeriodStatus.SUBMITTED:
                submitted_count += 1
            values = [
                period_start.strftime("%b %Y"),
                (period.status.value if period is not None else TimesheetPeriodStatus.OPEN.value).replace("_", " "),
                f"{sum(float(entry.hours or 0.0) for entry in entries):.2f}",
                period.submitted_by_username if period is not None and period.submitted_by_username else "-",
                period.decided_by_username if period is not None and period.decided_by_username else "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, period_start.isoformat())
                if col == 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.period_table.setItem(row_idx, col, item)
            if period_start == current_period:
                self.period_table.setRangeSelected(
                    QTableWidgetSelectionRange(row_idx, 0, row_idx, self.period_table.columnCount() - 1),
                    True,
                )
        if self._can_decide_period:
            self.period_queue_label.setText(
                f"Approval queue: {submitted_count} submitted period(s) awaiting a decision for this resource."
            )
        else:
            self.period_queue_label.setText(
                f"Resource review lane: {submitted_count} submitted period(s) currently waiting for approval."
            )

    def _sync_period_picker_from_table(self) -> None:
        row = self.period_table.currentRow()
        if row < 0:
            return
        item = self.period_table.item(row, 0)
        if item is None:
            return
        text = str(item.data(Qt.UserRole) or "").strip()
        if not text:
            return
        value = date.fromisoformat(text)
        current = self._current_period_start()
        if current == value:
            return
        self.period_edit.blockSignals(True)
        self.period_edit.setDate(QDate(value.year, value.month, value.day))
        self.period_edit.blockSignals(False)
        self.reload_entries()

    def _sync_period_action_state(
        self,
        *,
        period: TimesheetPeriod | None,
        has_task_entries: bool,
        has_resource_entries: bool,
    ) -> None:
        status = period.status if period is not None else TimesheetPeriodStatus.OPEN
        editable = self._can_manage_entries and status not in {
            TimesheetPeriodStatus.SUBMITTED,
            TimesheetPeriodStatus.APPROVED,
            TimesheetPeriodStatus.LOCKED,
        }
        self.btn_add.setEnabled(editable)
        self.btn_submit.setEnabled(
            self._can_manage_entries
            and has_resource_entries
            and status in {TimesheetPeriodStatus.OPEN, TimesheetPeriodStatus.REJECTED}
        )
        self.btn_approve.setEnabled(self._can_decide_period and period is not None and status == TimesheetPeriodStatus.SUBMITTED)
        self.btn_reject.setEnabled(self._can_decide_period and period is not None and status == TimesheetPeriodStatus.SUBMITTED)
        self.btn_lock.setEnabled(
            self._can_lock_period
            and status not in {TimesheetPeriodStatus.APPROVED, TimesheetPeriodStatus.LOCKED}
            and (has_resource_entries or period is not None)
        )
        self.btn_unlock.setEnabled(self._can_lock_period and period is not None and status == TimesheetPeriodStatus.LOCKED)
        self._row_actions_editable = editable and has_task_entries

    def _sync_row_action_state(self) -> None:
        has_selection = self._selected_entry_id() is not None
        self.btn_edit.setEnabled(self._row_actions_editable and has_selection)
        self.btn_delete.setEnabled(self._row_actions_editable and has_selection)

    def _selected_entry_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item is not None else None

    def _period_note(self, title: str, label: str) -> str | None:
        note, accepted = QInputDialog.getMultiLineText(
            self,
            title,
            label,
            "",
        )
        if not accepted:
            return None
        return note.strip()

    def _add_entry(self) -> None:
        dlg = TimeEntryEditDialog(self, default_date=self._current_period_start())
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            self._timesheet_service.add_time_entry(
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
        try:
            entry = self._timesheet_service.get_time_entry(entry_id)
        except NotFoundError:
            QMessageBox.warning(self, "Timesheet", "Selected entry no longer exists.")
            self.reload_entries()
            return
        dlg = TimeEntryEditDialog(self, entry=entry)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            self._timesheet_service.update_time_entry(
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
            self._timesheet_service.delete_time_entry(entry_id)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()

    def _submit_period(self) -> None:
        note = self._period_note("Submit Period", "Optional submission note:")
        if note is None:
            return
        try:
            self._timesheet_service.submit_timesheet_period(
                self._assignment.resource_id,
                period_start=self._current_period_start(),
                note=note,
            )
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()

    def _approve_period(self) -> None:
        period = self._timesheet_service.get_timesheet_period(
            self._assignment.resource_id,
            period_start=self._current_period_start(),
        )
        if period is None:
            QMessageBox.information(self, "Timesheet", "There is no submitted period to approve.")
            return
        note = self._period_note("Approve Period", "Optional approval note:")
        if note is None:
            return
        try:
            self._timesheet_service.approve_timesheet_period(period.id, note=note)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()

    def _reject_period(self) -> None:
        period = self._timesheet_service.get_timesheet_period(
            self._assignment.resource_id,
            period_start=self._current_period_start(),
        )
        if period is None:
            QMessageBox.information(self, "Timesheet", "There is no submitted period to reject.")
            return
        note = self._period_note("Reject Period", "Rejection note:")
        if note is None:
            return
        try:
            self._timesheet_service.reject_timesheet_period(period.id, note=note)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()

    def _lock_period(self) -> None:
        note = self._period_note("Lock Period", "Optional lock note:")
        if note is None:
            return
        try:
            self._timesheet_service.lock_timesheet_period(
                self._assignment.resource_id,
                period_start=self._current_period_start(),
                note=note,
            )
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()

    def _unlock_period(self) -> None:
        period = self._timesheet_service.get_timesheet_period(
            self._assignment.resource_id,
            period_start=self._current_period_start(),
        )
        if period is None:
            QMessageBox.information(self, "Timesheet", "There is no locked period to unlock.")
            return
        note = self._period_note("Unlock Period", "Optional unlock note:")
        if note is None:
            return
        try:
            self._timesheet_service.unlock_timesheet_period(period.id, note=note)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet", str(exc))
            return
        self.reload_entries()


__all__ = ["TimeEntryEditDialog", "TimesheetDialog"]
