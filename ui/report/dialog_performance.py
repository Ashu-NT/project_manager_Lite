from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from core.services.reporting import ReportingService
from ui.report.dialog_helpers import setup_dialog_size, soft_brush
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


def _fmt_money(value: float) -> str:
    return f"{float(value):,.2f}"


class PerformanceVarianceDialog(QDialog):
    def __init__(self, parent, reporting_service: ReportingService, project_id: str, project_name: str):
        super().__init__(parent)
        self._reporting_service: ReportingService = reporting_service
        self._project_id: str = project_id
        self._project_name: str = project_name
        self.setWindowTitle(f"Performance Variance - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        rows_variance = self._reporting_service.get_baseline_schedule_variance(self._project_id)
        rows_cost = self._reporting_service.get_cost_breakdown(self._project_id)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        setup_dialog_size(self, 980, 620, 1180, 760)

        title = QLabel(f"Performance Variance - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        subtitle = QLabel(
            "Combined view of schedule drift against baseline and planned-vs-actual cost breakdown."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(subtitle)

        grp_sched = QGroupBox("Schedule Variance (Baseline vs Current)")
        grp_sched.setFont(CFG.GROUPBOX_TITLE_FONT)
        sched_layout = QVBoxLayout(grp_sched)
        sched_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        sched_layout.setSpacing(CFG.SPACING_SM)

        tbl_sched = QTableWidget(len(rows_variance), 6)
        tbl_sched.setHorizontalHeaderLabels(
            ["Task", "Baseline Finish", "Current Finish", "Finish Variance (d)", "Start Variance (d)", "Critical"]
        )
        style_table(tbl_sched)
        tbl_sched.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3, 4, 5):
            tbl_sched.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)

        delayed_critical = 0
        for row, item in enumerate(rows_variance):
            finish_var = int(item.finish_variance_days or 0)
            start_var = int(item.start_variance_days or 0)
            if item.is_critical and finish_var > 0:
                delayed_critical += 1

            cells = [
                QTableWidgetItem(item.task_name),
                QTableWidgetItem(item.baseline_finish.isoformat() if item.baseline_finish else "-"),
                QTableWidgetItem(item.current_finish.isoformat() if item.current_finish else "-"),
                QTableWidgetItem(str(finish_var)),
                QTableWidgetItem(str(start_var)),
                QTableWidgetItem("Yes" if item.is_critical else "No"),
            ]
            cells[3].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cells[4].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tbl_sched.setItem(row, 0, cells[0])
            tbl_sched.setItem(row, 1, cells[1])
            tbl_sched.setItem(row, 2, cells[2])
            tbl_sched.setItem(row, 3, cells[3])
            tbl_sched.setItem(row, 4, cells[4])
            tbl_sched.setItem(row, 5, cells[5])

            if finish_var > 0:
                bg = soft_brush(CFG.COLOR_WARNING, 30)
                if item.is_critical:
                    bg = soft_brush(CFG.COLOR_DANGER, 36)
                for col in range(6):
                    tbl_sched.item(row, col).setBackground(bg)
        sched_layout.addWidget(tbl_sched)
        sched_info = QLabel(
            f"Variance rows: {len(rows_variance)} | Delayed critical tasks: {delayed_critical}"
        )
        sched_info.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        sched_layout.addWidget(sched_info)
        layout.addWidget(grp_sched, 1)

        grp_cost = QGroupBox("Cost Breakdown (Planned vs Actual)")
        grp_cost.setFont(CFG.GROUPBOX_TITLE_FONT)
        cost_layout = QVBoxLayout(grp_cost)
        cost_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        cost_layout.setSpacing(CFG.SPACING_SM)

        tbl_cost = QTableWidget(len(rows_cost), 5)
        tbl_cost.setHorizontalHeaderLabels(["Type", "Currency", "Planned", "Actual", "Variance"])
        style_table(tbl_cost)
        tbl_cost.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3, 4):
            tbl_cost.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)

        overrun_lines = 0
        for row, line in enumerate(rows_cost):
            variance = float(line.actual or 0.0) - float(line.planned or 0.0)
            if variance > 0:
                overrun_lines += 1

            values = [
                QTableWidgetItem(str(line.cost_type)),
                QTableWidgetItem(str(line.currency)),
                QTableWidgetItem(_fmt_money(float(line.planned or 0.0))),
                QTableWidgetItem(_fmt_money(float(line.actual or 0.0))),
                QTableWidgetItem(_fmt_money(variance)),
            ]
            for col in (2, 3, 4):
                values[col].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if variance > 0:
                values[4].setForeground(QBrush(QColor(CFG.COLOR_DANGER)))
            elif variance < 0:
                values[4].setForeground(QBrush(QColor(CFG.COLOR_SUCCESS)))
            for col, cell in enumerate(values):
                tbl_cost.setItem(row, col, cell)
        cost_layout.addWidget(tbl_cost)
        cost_info = QLabel(f"Cost categories: {len(rows_cost)} | Overrun lines: {overrun_lines}")
        cost_info.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        cost_layout.addWidget(cost_info)
        layout.addWidget(grp_cost, 1)

        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setFixedHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


__all__ = ["PerformanceVarianceDialog"]

