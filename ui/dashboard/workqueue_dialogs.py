from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class DashboardAlertsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard Alerts")
        self.resize(980, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)

        head = QHBoxLayout()
        self.summary_lbl = QLabel("0 active alerts")
        self.summary_lbl.setStyleSheet(
            f"font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY}; font-size: 10pt;"
        )
        head.addWidget(self.summary_lbl)
        head.addStretch()
        layout.addLayout(head)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Severity", "Issue", "Recommended Action"])
        style_table(self.table)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)

    def set_alert_rows(self, rows: list[tuple[str, str, str]], summary_text: str) -> None:
        self.summary_lbl.setText(summary_text)
        self.table.setRowCount(len(rows))
        for row, (severity, issue, action) in enumerate(rows):
            sev_item = QTableWidgetItem(severity)
            issue_item = QTableWidgetItem(issue)
            action_item = QTableWidgetItem(action)
            if severity == "HIGH":
                sev_item.setForeground(QColor(CFG.COLOR_DANGER))
            elif severity == "MEDIUM":
                sev_item.setForeground(QColor(CFG.COLOR_WARNING))
            else:
                sev_item.setForeground(QColor(CFG.COLOR_TEXT_SECONDARY))
            issue_item.setToolTip(issue)
            action_item.setToolTip(action)
            self.table.setItem(row, 0, sev_item)
            self.table.setItem(row, 1, issue_item)
            self.table.setItem(row, 2, action_item)


class DashboardUpcomingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upcoming Tasks (Next 14 Days)")
        self.resize(980, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)

        self.summary_lbl = QLabel("0 upcoming tasks")
        self.summary_lbl.setStyleSheet(
            f"font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY}; font-size: 10pt;"
        )
        layout.addWidget(self.summary_lbl)

        self.table = QTableWidget(0, len(CFG.UPCOMING_TASKS_HEADERS))
        self.table.setHorizontalHeaderLabels(CFG.UPCOMING_TASKS_HEADERS)
        style_table(self.table)
        self.table.setWordWrap(True)
        self._apply_stretch_columns()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setMinimumHeight(420)
        layout.addWidget(self.table, 1)
        layout.setStretch(1, 1)

    def set_upcoming_rows(self, rows: list[dict[str, object]]) -> None:
        self.summary_lbl.setText(f"{len(rows)} upcoming task(s)")
        self.table.setRowCount(0)
        if not rows:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, len(CFG.UPCOMING_TASKS_HEADERS))
            empty = QTableWidgetItem("No upcoming tasks in the next 14 days.")
            empty.setTextAlignment(Qt.AlignCenter)
            empty.setForeground(QColor(CFG.COLOR_TEXT_SECONDARY))
            empty.setFlags(empty.flags() & ~Qt.ItemIsSelectable)
            self.table.setItem(0, 0, empty)
            QTimer.singleShot(0, self._apply_stretch_columns)
            return

        self.table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = [
                str(item.get("name", "-")),
                str(item.get("start_date", "-")),
                str(item.get("end_date", "-")),
                str(item.get("progress", "-")),
                str(item.get("resource", "-")),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 3:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, cell)
            if bool(item.get("is_late")):
                for col in range(len(values)):
                    late_cell = self.table.item(row, col)
                    if late_cell:
                        late_cell.setBackground(QColor("#ffe5e5"))
        QTimer.singleShot(0, self._apply_stretch_columns)

    def _apply_stretch_columns(self) -> None:
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Stretch)


class DashboardConflictsDialog(QDialog):
    def __init__(self, conflicts_panel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resource Conflicts")
        self.resize(1040, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)
        layout.addWidget(conflicts_panel)


__all__ = [
    "DashboardAlertsDialog",
    "DashboardUpcomingDialog",
    "DashboardConflictsDialog",
]
