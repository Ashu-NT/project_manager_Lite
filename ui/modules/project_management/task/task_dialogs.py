from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core.platform.common.models import Task, TaskStatus
from ui.platform.shared.styles.ui_config import UIConfig as CFG
from ui.modules.project_management.task.task_progress_dialog import TaskProgressDialog


class TaskEditDialog(QDialog):
    def __init__(self, parent=None, task: Task | None = None):
        super().__init__(parent)
        self.setWindowTitle("Task" + (" - Edit" if task else " - New"))
        self._task: Task | None = task
        self._status_transition_kwargs: dict[str, object] = {}

        self.name_edit = QLineEdit()
        self.name_edit.setSizePolicy(CFG.INPUT_POLICY)
        self.name_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        self.name_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.desc_edit = QTextEdit()
        self.desc_edit.setSizePolicy(CFG.TEXTEDIT_POLICY)
        self.desc_edit.setMinimumHeight(CFG.TEXTEDIT_MIN_HEIGHT)

        self.status_combo = QComboBox()
        self.status_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.status_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self._status_values: list[TaskStatus] = [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.DONE,
            TaskStatus.BLOCKED,
        ]
        for s in self._status_values:
            self.status_combo.addItem(s.value, userData=s)

        self.start_date_edit = QDateEdit()
        self.deadline_edit = QDateEdit()
        for date_edit in (self.start_date_edit, self.deadline_edit):
            date_edit.setSizePolicy(CFG.INPUT_POLICY)
            date_edit.setFixedHeight(CFG.INPUT_HEIGHT)
            date_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat(CFG.DATE_FORMAT)

        self.duration_spin = QSpinBox()
        self.duration_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.duration_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.duration_spin.setMinimum(CFG.MIN_VALUE)
        self.duration_spin.setMaximum(CFG.DURATION_MAX)

        self.priority_spin = QSpinBox()
        self.priority_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.priority_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.priority_spin.setMinimum(CFG.MIN_VALUE)
        self.priority_spin.setMaximum(CFG.PRIORITY_MAX)

        if task:
            self.name_edit.setText(task.name)
            self.desc_edit.setPlainText(task.description or "")
            for i, s in enumerate(self._status_values):
                if s == task.status:
                    self.status_combo.setCurrentIndex(i)
                    break
            if task.start_date:
                self.start_date_edit.setDate(
                    QDate(task.start_date.year, task.start_date.month, task.start_date.day)
                )
            if getattr(task, "deadline", None):
                d = task.deadline
                self.deadline_edit.setDate(QDate(d.year, d.month, d.day))
            if task.duration_days is not None:
                self.duration_spin.setValue(task.duration_days)
            if task.priority is not None:
                self.priority_spin.setValue(task.priority)
        else:
            today = QDate.currentDate()
            self.start_date_edit.setDate(today)
            self.deadline_edit.setDate(today)
            self.status_combo.setCurrentIndex(0)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)

        form.addRow("Name:", self.name_edit)
        form.addRow("Description:", self.desc_edit)
        form.addRow("Status:", self.status_combo)
        form.addRow("Start date:", self.start_date_edit)
        form.addRow("Duration (working days):", self.duration_spin)
        form.addRow("Deadline:", self.deadline_edit)
        form.addRow("Priority:", self.priority_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setCenterButtons(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setMinimumSize(self.sizeHint())

    def _prompt_iso_date(self, title: str, prompt: str, seed: date | None = None) -> date | None:
        default_date = seed or date.today()
        while True:
            raw_text, ok = QInputDialog.getText(
                self,
                title,
                prompt,
                text=default_date.isoformat(),
            )
            if not ok:
                return None
            value = str(raw_text or "").strip()
            try:
                return date.fromisoformat(value)
            except ValueError:
                QMessageBox.warning(self, title, "Enter a valid date as YYYY-MM-DD.")

    def _collect_status_transition_kwargs(self) -> dict[str, object] | None:
        if self._task is None:
            return {}

        previous_status = self._task.status
        target_status = self.status
        if target_status == previous_status:
            return {}

        payload: dict[str, object] = {}
        if previous_status == TaskStatus.DONE and target_status != TaskStatus.DONE:
            decision = QMessageBox.question(
                self,
                "Reopen completed task",
                "This task is already Done. Do you want to change it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if decision != QMessageBox.Yes:
                return None

        if target_status == TaskStatus.DONE:
            payload["percent_complete"] = 100.0
            actual_end = self._prompt_iso_date(
                "Actual end date",
                "Enter actual end date (YYYY-MM-DD):",
                seed=getattr(self._task, "actual_end", None) or getattr(self._task, "end_date", None),
            )
            if actual_end is None:
                return None
            payload["actual_end"] = actual_end
        elif target_status == TaskStatus.TODO:
            payload["percent_complete"] = 0.0
        elif previous_status == TaskStatus.TODO and target_status == TaskStatus.IN_PROGRESS:
            actual_start = self._prompt_iso_date(
                "Actual start date",
                "Enter actual start date (YYYY-MM-DD):",
                seed=getattr(self._task, "actual_start", None) or self.start_date,
            )
            if actual_start is None:
                return None
            payload["actual_start"] = actual_start
        elif previous_status == TaskStatus.DONE and target_status == TaskStatus.IN_PROGRESS:
            current_progress = float(getattr(self._task, "percent_complete", 100.0) or 100.0)
            default_progress = max(1.0, min(99.0, current_progress if current_progress < 100.0 else 50.0))
            percent, ok = QInputDialog.getDouble(
                self,
                "Completion percentage",
                "Enter completion % for In Progress:",
                default_progress,
                1.0,
                99.0,
                1,
            )
            if not ok:
                return None
            payload["percent_complete"] = float(percent)

        return payload

    def accept(self) -> None:
        payload = self._collect_status_transition_kwargs()
        if payload is None:
            return
        self._status_transition_kwargs = payload
        super().accept()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def description(self) -> str:
        return self.desc_edit.toPlainText().strip()

    @property
    def status(self) -> TaskStatus:
        idx = self.status_combo.currentIndex()
        if 0 <= idx < len(self._status_values):
            return self._status_values[idx]
        return TaskStatus.TODO

    @property
    def start_date(self) -> date | None:
        qd = self.start_date_edit.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    @property
    def duration_days(self) -> int | None:
        val = self.duration_spin.value()
        return val if val > 0 else None

    @property
    def deadline(self) -> date | None:
        qd = self.deadline_edit.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    @property
    def priority(self) -> int | None:
        val = self.priority_spin.value()
        return val if val > 0 else None

    @property
    def status_transition_kwargs(self) -> dict[str, object]:
        return dict(self._status_transition_kwargs)


__all__ = ["TaskEditDialog", "TaskProgressDialog"]
