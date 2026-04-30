from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QVBoxLayout,
)

from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.domain.enums import TaskStatus
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class TaskProgressDialog(QDialog):
    def __init__(self, parent=None, task: Task | None = None):
        super().__init__(parent)
        self.setWindowTitle("Update progress")
        self._task: Task | None = task

        self.percent_check = QCheckBox()
        self.percent_check.setToolTip("Enable to update percent complete")

        self.percent_spin = QDoubleSpinBox()
        self.percent_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.percent_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.percent_spin.setMinimum(CFG.MONEY_MIN)
        self.percent_spin.setMaximum(CFG.PERCENTAGE_MAX)
        self.percent_spin.setDecimals(CFG.PERCENT_DECIMALS)
        self.percent_spin.setSingleStep(CFG.PERCENTAGE_STEP)
        self.percent_spin.setAlignment(CFG.ALIGN_RIGHT)

        self.actual_start_check = QCheckBox()
        self.actual_start_check.setToolTip("Enable to update actual start date")
        self.actual_end_check = QCheckBox()
        self.actual_end_check.setToolTip("Enable to update actual end date")
        self.status_check = QCheckBox()
        self.status_check.setToolTip("Enable to update task status")

        self.status_combo = QComboBox()
        self.status_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.status_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self._status_values: list[TaskStatus] = [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.DONE,
            TaskStatus.BLOCKED,
        ]
        for status in self._status_values:
            self.status_combo.addItem(status.value, userData=status)

        self.actual_start_edit = QDateEdit()
        self.actual_end_edit = QDateEdit()
        today = QDate.currentDate()
        for date_edit in (self.actual_start_edit, self.actual_end_edit):
            date_edit.setSizePolicy(CFG.INPUT_POLICY)
            date_edit.setFixedHeight(CFG.INPUT_HEIGHT)
            date_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat(CFG.DATE_FORMAT)
            date_edit.setDate(today)

        for chkbox in (
            self.percent_check,
            self.actual_start_check,
            self.actual_end_check,
            self.status_check,
        ):
            chkbox.setSizePolicy(CFG.CHECKBOX_POLICY)
            chkbox.setFixedHeight(CFG.CHECKBOX_HEIGHT)

        self.percent_check.setChecked(True)
        if task:
            if task.percent_complete is not None:
                self.percent_spin.setValue(task.percent_complete)
            for i, status in enumerate(self._status_values):
                if status == task.status:
                    self.status_combo.setCurrentIndex(i)
                    break
            if task.actual_start:
                self.actual_start_edit.setDate(
                    QDate(task.actual_start.year, task.actual_start.month, task.actual_start.day)
                )
            if task.actual_end:
                self.actual_end_edit.setDate(
                    QDate(task.actual_end.year, task.actual_end.month, task.actual_end.day)
                )
        self.actual_start_check.setChecked(False)
        self.actual_end_check.setChecked(False)
        self.status_check.setChecked(False)

        self.percent_check.toggled.connect(self.percent_spin.setEnabled)
        self.actual_start_check.toggled.connect(self.actual_start_edit.setEnabled)
        self.actual_end_check.toggled.connect(self.actual_end_edit.setEnabled)
        self.status_check.toggled.connect(self.status_combo.setEnabled)

        self.percent_spin.setEnabled(self.percent_check.isChecked())
        self.actual_start_edit.setEnabled(self.actual_start_check.isChecked())
        self.actual_end_edit.setEnabled(self.actual_end_check.isChecked())
        self.status_combo.setEnabled(self.status_check.isChecked())

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)

        form.addRow("Percent complete:", self._with_checkbox(self.percent_spin, self.percent_check))
        form.addRow("Actual start:", self._with_checkbox(self.actual_start_edit, self.actual_start_check))
        form.addRow("Actual end:", self._with_checkbox(self.actual_end_edit, self.actual_end_check))
        form.addRow("Status:", self._with_checkbox(self.status_combo, self.status_check))

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

    @staticmethod
    def _with_checkbox(editor, checkbox: QCheckBox) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(CFG.SPACING_SM)
        row.addWidget(editor)
        row.addWidget(checkbox)
        return row

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

    def build_payload(self) -> dict[str, object] | None:
        payload: dict[str, object] = {}
        if self.percent_set:
            payload["percent_complete"] = self.percent_complete
        if self.actual_start_set:
            payload["actual_start"] = self.actual_start
        if self.actual_end_set:
            payload["actual_end"] = self.actual_end
        if self.status_set and self.status is not None:
            payload["status"] = self.status

        if self._task is None:
            return payload
        target_status = self.status
        if not self.status_set or target_status is None or target_status == self._task.status:
            return payload

        previous_status = self._task.status
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
            if payload.get("actual_end") is None:
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
            if payload.get("actual_start") is None:
                actual_start = self._prompt_iso_date(
                    "Actual start date",
                    "Enter actual start date (YYYY-MM-DD):",
                    seed=getattr(self._task, "actual_start", None) or getattr(self._task, "start_date", None),
                )
                if actual_start is None:
                    return None
                payload["actual_start"] = actual_start
        elif previous_status == TaskStatus.DONE and target_status == TaskStatus.IN_PROGRESS:
            current_progress = float(payload.get("percent_complete", getattr(self._task, "percent_complete", 100.0) or 100.0))
            if not 0.0 < current_progress < 100.0:
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

    @property
    def percent_set(self) -> bool:
        return bool(self.percent_check.isChecked())

    @property
    def actual_start_set(self) -> bool:
        return bool(self.actual_start_check.isChecked())

    @property
    def actual_end_set(self) -> bool:
        return bool(self.actual_end_check.isChecked())

    @property
    def status_set(self) -> bool:
        return bool(self.status_check.isChecked())

    @property
    def percent_complete(self) -> float | None:
        if not self.percent_set:
            return None
        return self.percent_spin.value()

    @property
    def actual_start(self) -> date | None:
        if not self.actual_start_set:
            return None
        qd = self.actual_start_edit.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    @property
    def actual_end(self) -> date | None:
        if not self.actual_end_set:
            return None
        qd = self.actual_end_edit.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    @property
    def status(self) -> TaskStatus | None:
        if not self.status_set:
            return None
        idx = self.status_combo.currentIndex()
        if 0 <= idx < len(self._status_values):
            return self._status_values[idx]
        return TaskStatus.TODO


__all__ = ["TaskProgressDialog"]
