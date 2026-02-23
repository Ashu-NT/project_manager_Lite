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
from ui.report.dialog_helpers import metric_card, setup_dialog_size, soft_brush
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class ResourceLoadDialog(QDialog):
    def __init__(self, parent, reporting_service: ReportingService, project_id: str, project_name: str):
        super().__init__(parent)
        self._reporting_service: ReportingService = reporting_service
        self._project_id: str = project_id
        self._project_name: str = project_name
        self.setWindowTitle(f"Resource Load - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        setup_dialog_size(self, 900, 520, 1080, 660)

        title = QLabel(f"Resource Load - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        info = QLabel(
            "Capacity overview by resource. "
            "Values above 100% indicate over-allocation risk."
        )
        info.setWordWrap(True)
        info.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(info)

        rows = self._reporting_service.get_resource_load_summary(self._project_id)
        overloaded = [r for r in rows if r.total_allocation_percent > 100.0]
        avg_load = (
            sum(r.total_allocation_percent for r in rows) / len(rows) if rows else 0.0
        )

        cards_row = QHBoxLayout()
        cards_row.setSpacing(CFG.SPACING_SM)
        cards_row.addWidget(
            metric_card(
                "Resources",
                str(len(rows)),
                "Assigned in current project",
                CFG.COLOR_ACCENT,
            )
        )
        cards_row.addWidget(
            metric_card(
                "Overloaded",
                str(len(overloaded)),
                "Above 100% allocation",
                CFG.COLOR_DANGER,
            )
        )
        cards_row.addWidget(
            metric_card(
                "Average Load",
                f"{avg_load:.1f}%",
                "Across assigned resources",
                CFG.COLOR_WARNING,
            )
        )
        layout.addLayout(cards_row)

        headers = ["Resource", "Total Allocation (%)", "Tasks", "Status"]
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        style_table(table)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.setSortingEnabled(True)

        for i, row in enumerate(rows):
            name_item = QTableWidgetItem(row.resource_name)
            name_item.setToolTip(f"Resource ID: {row.resource_id}")
            alloc_item = QTableWidgetItem(f"{row.total_allocation_percent:.1f}%")
            alloc_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tasks_item = QTableWidgetItem(str(row.tasks_count))
            tasks_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if row.total_allocation_percent > 120.0:
                status_text, fg, row_bg = "Overloaded", CFG.COLOR_DANGER, soft_brush(CFG.COLOR_DANGER, 34)
            elif row.total_allocation_percent > 100.0:
                status_text, fg, row_bg = "Risk", CFG.COLOR_WARNING, soft_brush(CFG.COLOR_WARNING, 34)
            elif row.total_allocation_percent >= 80.0:
                status_text, fg, row_bg = "High", CFG.COLOR_ACCENT, soft_brush(CFG.COLOR_ACCENT, 32)
            else:
                status_text, fg, row_bg = "Balanced", CFG.COLOR_SUCCESS, soft_brush(CFG.COLOR_SUCCESS, 32)

            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QBrush(QColor(fg)))
            alloc_item.setForeground(QBrush(QColor(fg)))

            table.setItem(i, 0, name_item)
            table.setItem(i, 1, alloc_item)
            table.setItem(i, 2, tasks_item)
            table.setItem(i, 3, status_item)

            for col in range(len(headers)):
                table.item(i, col).setBackground(row_bg)

        if not rows:
            table.setRowCount(1)
            table.setItem(0, 0, QTableWidgetItem("No resource assignments for this project."))
            for col in range(1, len(headers)):
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
