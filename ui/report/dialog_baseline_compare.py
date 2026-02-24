from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QDialog,
)

from core.exceptions import DomainError
from core.services.reporting import ReportingService
from ui.report.dialog_helpers import setup_dialog_size, soft_brush
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


def _fmt_date(value) -> str:
    return value.isoformat() if value else "-"


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f}"


def _fmt_delta(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{value:+d}"


class BaselineCompareDialog(QDialog):
    def __init__(self, parent, reporting_service: ReportingService, project_id: str, project_name: str):
        super().__init__(parent)
        self._reporting_service: ReportingService = reporting_service
        self._project_id: str = project_id
        self._project_name: str = project_name
        self.setWindowTitle(f"Baseline Comparison - {project_name}")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        setup_dialog_size(self, 1040, 620, 1220, 760)

        title = QLabel(f"Baseline Comparison - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        subtitle = QLabel(
            "Compare two baseline snapshots to understand scope, schedule, and planning-cost drift."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(subtitle)

        selector_row = QHBoxLayout()
        selector_row.setSpacing(CFG.SPACING_SM)

        selector_row.addWidget(QLabel("From baseline:"))
        self.cmb_baseline_a = QComboBox()
        self.cmb_baseline_a.setSizePolicy(CFG.INPUT_POLICY)
        self.cmb_baseline_a.setMinimumHeight(CFG.INPUT_HEIGHT)
        self.cmb_baseline_a.setEditable(False)
        selector_row.addWidget(self.cmb_baseline_a, 1)

        selector_row.addWidget(QLabel("To baseline:"))
        self.cmb_baseline_b = QComboBox()
        self.cmb_baseline_b.setSizePolicy(CFG.INPUT_POLICY)
        self.cmb_baseline_b.setMinimumHeight(CFG.INPUT_HEIGHT)
        self.cmb_baseline_b.setEditable(False)
        selector_row.addWidget(self.cmb_baseline_b, 1)

        self.chk_show_unchanged = QCheckBox("Show unchanged tasks")
        selector_row.addWidget(self.chk_show_unchanged)

        self.btn_compare = QPushButton("Compare")
        self.btn_compare.setMinimumHeight(CFG.BUTTON_HEIGHT)
        self.btn_compare.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        selector_row.addWidget(self.btn_compare)
        layout.addLayout(selector_row)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        headers = [
            "Task",
            "From Start",
            "To Start",
            "Delta Start (d)",
            "From Finish",
            "To Finish",
            "Delta Finish (d)",
            "From Cost",
            "To Cost",
            "Delta Cost",
            "Change",
        ]
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        style_table(self.table)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.horizontalHeader().resizeSection(0, 320)
        for col in range(1, len(headers)):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
            self.table.horizontalHeader().resizeSection(col, 120 if col not in (10,) else 110)
        layout.addWidget(self.table, 1)

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setMinimumHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        layout.addLayout(close_row)

        self.btn_compare.clicked.connect(self._run_compare)
        self.chk_show_unchanged.toggled.connect(lambda _checked: self._run_compare())
        self._load_baselines()

    def _load_baselines(self) -> None:
        baselines = self._reporting_service.list_project_baselines(self._project_id)
        self.cmb_baseline_a.clear()
        self.cmb_baseline_b.clear()

        for baseline in baselines:
            label = f"{baseline.name} ({baseline.created_at.isoformat()})"
            self.cmb_baseline_a.addItem(label, userData=baseline.id)
            self.cmb_baseline_b.addItem(label, userData=baseline.id)

        can_compare = len(baselines) >= 2
        self.cmb_baseline_a.setEnabled(can_compare)
        self.cmb_baseline_b.setEnabled(can_compare)
        self.chk_show_unchanged.setEnabled(can_compare)
        self.btn_compare.setEnabled(can_compare)

        if not can_compare:
            self.summary_label.setText("At least two baselines are required for comparison.")
            self.table.setRowCount(0)
            return

        # list_for_project returns newest first; default compare older -> newer
        self.cmb_baseline_a.setCurrentIndex(1)
        self.cmb_baseline_b.setCurrentIndex(0)
        self._run_compare()

    def _run_compare(self) -> None:
        if not self.btn_compare.isEnabled():
            return

        baseline_a_id = self.cmb_baseline_a.currentData()
        baseline_b_id = self.cmb_baseline_b.currentData()
        if not baseline_a_id or not baseline_b_id:
            return
        if baseline_a_id == baseline_b_id:
            self.summary_label.setText("Select two different baselines to compare.")
            self.table.setRowCount(0)
            return

        try:
            result = self._reporting_service.compare_baselines(
                project_id=self._project_id,
                baseline_a_id=baseline_a_id,
                baseline_b_id=baseline_b_id,
                include_unchanged=self.chk_show_unchanged.isChecked(),
            )
        except DomainError as exc:
            QMessageBox.warning(self, "Baseline Comparison", str(exc))
            return
        except Exception as exc:
            QMessageBox.warning(self, "Baseline Comparison", f"Failed to compare baselines: {exc}")
            return

        self.summary_label.setText(
            f"From '{result.baseline_a_name}' to '{result.baseline_b_name}' | "
            f"Compared: {result.total_tasks_compared} tasks | "
            f"Changed: {result.changed_tasks} | Added: {result.added_tasks} | "
            f"Removed: {result.removed_tasks} | Unchanged: {result.unchanged_tasks}"
        )

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(result.rows))
        for row_idx, row in enumerate(result.rows):
            change = row.change_type
            row_bg = {
                "ADDED": soft_brush(CFG.COLOR_SUCCESS, 30),
                "REMOVED": soft_brush(CFG.COLOR_DANGER, 34),
                "CHANGED": soft_brush(CFG.COLOR_WARNING, 30),
                "UNCHANGED": soft_brush(CFG.COLOR_ACCENT, 20),
            }.get(change, soft_brush(CFG.COLOR_ACCENT, 16))

            values = [
                row.task_name,
                _fmt_date(row.baseline_a_start),
                _fmt_date(row.baseline_b_start),
                _fmt_delta(row.start_shift_days),
                _fmt_date(row.baseline_a_finish),
                _fmt_date(row.baseline_b_finish),
                _fmt_delta(row.finish_shift_days),
                _fmt_money(row.baseline_a_planned_cost),
                _fmt_money(row.baseline_b_planned_cost),
                _fmt_money(row.planned_cost_delta),
                change.title(),
            ]

            for col_idx, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if col_idx in (3, 6, 7, 8, 9):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col_idx == 10:
                    fg = {
                        "ADDED": CFG.COLOR_SUCCESS,
                        "REMOVED": CFG.COLOR_DANGER,
                        "CHANGED": CFG.COLOR_WARNING,
                        "UNCHANGED": CFG.COLOR_TEXT_SECONDARY,
                    }.get(change, CFG.COLOR_TEXT_PRIMARY)
                    item.setForeground(QBrush(QColor(fg)))
                self.table.setItem(row_idx, col_idx, item)
                if col_idx == 10:
                    self.table.item(row_idx, col_idx).setBackground(row_bg)

        if not result.rows:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No changes to display for selected filter."))
            for col in range(1, self.table.columnCount()):
                self.table.setItem(0, col, QTableWidgetItem(""))

        self.table.setSortingEnabled(True)


__all__ = ["BaselineCompareDialog"]
