from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from core.services.reporting.models import ResourceLoadRow
from core.services.dashboard import DashboardData
from core.services.scheduling.leveling_models import ResourceConflict
from ui.styles.ui_config import UIConfig as CFG


class DashboardAlertsRenderingMixin:
    conflicts_table: QTableWidget

    def _update_alerts(self, data: DashboardData):
        alerts = data.alerts or []
        alert_rows: list[tuple[str, str, str]] = []
        summary = "0 active alerts"
        if not alerts:
            alert_rows.append(("OK", "No active alerts", "No action required"))
            badge_variant = "success"
        else:
            high = 0
            medium = 0
            low = 0
            for msg in alerts:
                severity, action = self._classify_alert(msg)
                if severity == "HIGH":
                    high += 1
                elif severity == "MEDIUM":
                    medium += 1
                else:
                    low += 1
                alert_rows.append((severity, msg, action))
            summary = f"{len(alerts)} active alerts  |  H:{high}  M:{medium}  L:{low}"
            badge_variant = "danger" if high else ("warning" if medium else "info")

        self._current_alert_rows = alert_rows
        self._current_alert_summary = summary
        self.btn_open_alerts.set_badge(len(alerts), badge_variant)

        dlg = getattr(self, "_alerts_dialog", None)
        if dlg is not None and dlg.isVisible():
            dlg.set_alert_rows(alert_rows, summary)

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

    @staticmethod
    def _classify_alert(message: str) -> tuple[str, str]:
        text = (message or "").lower()
        if "overloaded" in text or "over-allocated" in text:
            return "HIGH", "Run Auto-Level or shift a task in Resource Conflicts."
        if "late" in text or "delayed" in text or "missed its deadline" in text:
            return "MEDIUM", "Review schedule and baseline variance."
        return "LOW", "Inspect task data quality and dates."


__all__ = ["DashboardAlertsRenderingMixin"]
