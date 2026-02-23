from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.services.reporting import ReportingService
from ui.report.dialog_helpers import setup_dialog_size, soft_brush
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class CriticalPathDialog(QDialog):
    def __init__(self, parent, reporting_service: ReportingService, project_id: str, project_name: str):
        super().__init__(parent)
        self._reporting_service = reporting_service
        self._project_id = project_id
        self._project_name = project_name
        self.setWindowTitle(f"Critical Path - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        setup_dialog_size(self, 920, 520, 1120, 680)

        title = QLabel(f"Critical Path - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        info_label = QLabel(
            "These tasks define the minimum project duration. "
            "Delay on any of them typically delays the entire project."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(info_label)

        critical = self._reporting_service.get_critical_path(self._project_id)
        if critical:
            starts = [item.earliest_start for item in critical if item.earliest_start]
            finishes = [item.earliest_finish for item in critical if item.earliest_finish]
            if starts and finishes:
                summary = (
                    f"Critical tasks: {len(critical)} | "
                    f"Path span: {min(starts).isoformat()} to {max(finishes).isoformat()}"
                )
            else:
                summary = f"Critical tasks: {len(critical)}"
        else:
            summary = "No critical tasks identified."
        summary_label = QLabel(summary)
        summary_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        layout.addWidget(summary_label)

        table = QTableWidget(len(critical), len(CFG.CRITICAL_PATH_HEADERS))
        table.setHorizontalHeaderLabels(CFG.CRITICAL_PATH_HEADERS)
        style_table(table)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, len(CFG.CRITICAL_PATH_HEADERS)):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)

        for row, item in enumerate(critical):
            task = item.task
            start = item.earliest_start
            finish = item.earliest_finish
            dur = (finish - start).days + 1 if (start and finish) else None
            status_text = str(getattr(task.status, "value", task.status or "-")).replace("_", " ").title()

            cells = [
                QTableWidgetItem(task.name),
                QTableWidgetItem(start.isoformat() if start else "-"),
                QTableWidgetItem(finish.isoformat() if finish else "-"),
                QTableWidgetItem(str(dur) if dur is not None else "-"),
                QTableWidgetItem(str(item.total_float_days)),
                QTableWidgetItem(status_text),
            ]
            cells[3].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cells[4].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            for col, cell in enumerate(cells):
                table.setItem(row, col, cell)

            row_bg = soft_brush(CFG.COLOR_DANGER, 34)
            for col in range(len(cells)):
                table.item(row, col).setBackground(row_bg)

        if not critical:
            table.setRowCount(1)
            msg = QTableWidgetItem("No critical tasks to display.")
            msg.setForeground(QBrush(QColor(CFG.COLOR_TEXT_MUTED)))
            table.setItem(0, 0, msg)
            for col in range(1, len(CFG.CRITICAL_PATH_HEADERS)):
                table.setItem(0, col, QTableWidgetItem(""))

        layout.addWidget(table)

        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setMinimumHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

