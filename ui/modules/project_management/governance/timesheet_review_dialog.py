from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.time.application.timesheet_review import (
    TimesheetReviewDetail,
    TimesheetReviewQueueItem,
)
from src.ui.shared.widgets.guards import has_permission
from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class TimesheetReviewDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        timesheet_service,
        summary: TimesheetReviewQueueItem,
        detail: TimesheetReviewDetail,
        project_name_by_id: dict[str, str],
        user_session=None,
    ) -> None:
        super().__init__(parent)
        self._timesheet_service = timesheet_service
        self._summary = summary
        self._detail = detail
        self._project_name_by_id = project_name_by_id
        self._can_decide = has_permission(user_session, "timesheet.approve")
        self.setWindowTitle(f"Timesheet Review - {summary.resource_name}")
        self.resize(920, 560)
        self._setup_ui()
        self._apply_detail()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_SM)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        self.title_label.setWordWrap(True)
        root.addWidget(self.title_label)

        self.meta_label = QLabel("")
        self.meta_label.setWordWrap(True)
        self.meta_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        root.addWidget(self.meta_label)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        root.addWidget(self.status_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Date", "Project", "Task", "Hours", "User", "Note"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        root.addWidget(self.table, 1)

        button_row = QHBoxLayout()
        self.btn_approve = QPushButton("Approve Period")
        self.btn_reject = QPushButton("Reject Period")
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for button in (self.btn_approve, self.btn_reject, self.btn_close):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            button_row.addWidget(button)
        button_row.addStretch()
        root.addLayout(button_row)

        self.btn_approve.clicked.connect(self._approve_period)
        self.btn_reject.clicked.connect(self._reject_period)
        self.btn_close.clicked.connect(self.accept)

    def _apply_detail(self) -> None:
        summary = self._detail.summary
        self._summary = summary
        projects = self._project_labels(summary.project_ids)
        self.title_label.setText(
            f"{summary.resource_name} | {summary.period_start.isoformat()} to {summary.period_end.isoformat()}"
        )
        self.meta_label.setText(
            f"Submitted by: {summary.submitted_by_username or 'system'} | "
            f"Hours: {summary.total_hours:.2f} across {summary.entry_count} entries | "
            f"Projects: {projects}"
        )
        note = summary.decision_note or "-"
        self.status_label.setText(f"Status: {summary.status.value} | Note: {note}")

        self.table.setRowCount(len(self._detail.entries))
        for row_idx, entry in enumerate(self._detail.entries):
            values = [
                entry.entry_date.isoformat(),
                self._project_name_by_id.get(entry.project_id or "", entry.project_id or "-"),
                entry.task_name or "-",
                f"{entry.hours:.2f}",
                entry.author_username or "unknown",
                entry.note or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 3:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_idx, col, item)
        can_decide = self._can_decide and summary.status.value == "SUBMITTED"
        self.btn_approve.setEnabled(can_decide)
        self.btn_reject.setEnabled(can_decide)

    def _approve_period(self) -> None:
        note, accepted = QInputDialog.getMultiLineText(
            self,
            "Approve Period",
            "Optional approval note:",
            "",
        )
        if not accepted:
            return
        try:
            self._timesheet_service.approve_timesheet_period(self._summary.period_id, note=note.strip())
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet Review", str(exc))
            return
        self.accept()

    def _reject_period(self) -> None:
        note, accepted = QInputDialog.getMultiLineText(
            self,
            "Reject Period",
            "Rejection note:",
            "",
        )
        if not accepted:
            return
        try:
            self._timesheet_service.reject_timesheet_period(self._summary.period_id, note=note.strip())
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Timesheet Review", str(exc))
            return
        self.accept()

    def _project_labels(self, project_ids: tuple[str, ...]) -> str:
        labels = [self._project_name_by_id.get(project_id, project_id) for project_id in project_ids]
        return ", ".join(labels) if labels else "-"


__all__ = ["TimesheetReviewDialog"]
