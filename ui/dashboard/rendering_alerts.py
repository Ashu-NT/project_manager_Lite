from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem

from core.services.reporting.models import ResourceLoadRow
from core.services.dashboard import DashboardData
from core.services.scheduling.leveling_models import ResourceConflict
from ui.styles.ui_config import UIConfig as CFG


class DashboardAlertsRenderingMixin:
    alerts_table: QTableWidget
    conflicts_table: QTableWidget
    alerts_status: QLabel

    def _update_alerts(self, data: DashboardData):
        alerts = data.alerts or []
        self.alerts_table.setRowCount(0)

        if not alerts:
            self.alerts_table.setRowCount(1)
            self._set_alert_row(0, "OK", "No active alerts", "No action required")
            self.alerts_status.setText("0 active alerts")
            self.alerts_status.setStyleSheet(
                f"font-weight: 700; color: {CFG.COLOR_SUCCESS}; font-size: 10pt;"
            )
            return

        high = 0
        medium = 0
        low = 0
        self.alerts_table.setRowCount(len(alerts))
        for row, msg in enumerate(alerts):
            severity, action = self._classify_alert(msg)
            if severity == "HIGH":
                high += 1
            elif severity == "MEDIUM":
                medium += 1
            else:
                low += 1
            self._set_alert_row(row, severity, msg, action)

        self.alerts_status.setText(
            f"{len(alerts)} active alerts  |  H:{high}  M:{medium}  L:{low}"
        )
        self.alerts_status.setStyleSheet(
            f"font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY}; font-size: 10pt;"
        )

    def _update_conflicts(self, conflicts: list[ResourceConflict]):
        self.conflicts_table.setRowCount(0)
        if not conflicts:
            self.conflicts_table.setRowCount(1)
            row = [
                QTableWidgetItem("-"),
                QTableWidgetItem("-"),
                QTableWidgetItem("No overload conflicts"),
                QTableWidgetItem("-"),
            ]
            for col, item in enumerate(row):
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                self.conflicts_table.setItem(0, col, item)
            return

        self.conflicts_table.setRowCount(len(conflicts))
        for row, conflict in enumerate(conflicts):
            task_preview = ", ".join(
                f"{e.task_name} ({e.allocation_percent:.0f}%)" for e in conflict.entries[:3]
            )
            if len(conflict.entries) > 3:
                task_preview += " ..."
            values = [
                conflict.resource_name,
                conflict.conflict_date.isoformat(),
                f"{conflict.total_allocation_percent:.1f}%",
                task_preview,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setForeground(QColor(CFG.COLOR_DANGER))
                if col == 3:
                    details = "\n".join(
                        f"- {e.task_name}: {e.allocation_percent:.1f}%"
                        for e in conflict.entries
                    )
                    item.setToolTip(details)
                self.conflicts_table.setItem(row, col, item)

    def _update_conflicts_from_load(self, rows: list[ResourceLoadRow]) -> None:
        self.conflicts_table.setRowCount(0)
        if not rows:
            self._update_conflicts([])
            return

        self.conflicts_table.setRowCount(len(rows))
        for row, load in enumerate(rows):
            vals = [
                load.resource_name,
                "-",
                f"{float(load.total_allocation_percent or 0.0):.1f}%",
                (
                    f"Aggregate {int(load.tasks_count or 0)} assignment(s); "
                    "no same-day overlap conflict detected."
                ),
            ]
            for col, value in enumerate(vals):
                item = QTableWidgetItem(value)
                if col == 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setForeground(QColor(CFG.COLOR_WARNING))
                if col == 3:
                    item.setToolTip(
                        "This row indicates allocation risk from aggregate project load. "
                        "Auto/manual leveling uses daily conflicts only."
                    )
                self.conflicts_table.setItem(row, col, item)

    def _set_alert_row(self, row: int, severity: str, issue: str, action: str) -> None:
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

        self.alerts_table.setItem(row, 0, sev_item)
        self.alerts_table.setItem(row, 1, issue_item)
        self.alerts_table.setItem(row, 2, action_item)

    @staticmethod
    def _classify_alert(message: str) -> tuple[str, str]:
        text = (message or "").lower()
        if "overloaded" in text or "over-allocated" in text:
            return "HIGH", "Run Auto-Level or shift a task in Resource Conflicts."
        if "late" in text or "delayed" in text or "missed its deadline" in text:
            return "MEDIUM", "Review schedule and baseline variance."
        return "LOW", "Inspect task data quality and dates."


__all__ = ["DashboardAlertsRenderingMixin"]
