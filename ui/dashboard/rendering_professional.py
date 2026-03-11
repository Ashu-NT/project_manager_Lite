from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGroupBox, QTableWidget, QTableWidgetItem

from core.services.dashboard import DashboardData
from ui.styles.ui_config import UIConfig as CFG


class DashboardProfessionalRenderingMixin:
    milestone_group: QGroupBox
    milestone_table: QTableWidget
    watchlist_group: QGroupBox
    watchlist_table: QTableWidget

    def _clear_professional_panels(self) -> None:
        if hasattr(self, "milestone_table"):
            self.milestone_table.setRowCount(0)
        if hasattr(self, "watchlist_table"):
            self.watchlist_table.setRowCount(0)
        if hasattr(self, "milestone_group"):
            self.milestone_group.setTitle("Milestone Health")
        if hasattr(self, "watchlist_group"):
            self.watchlist_group.setTitle("Critical Path Watchlist")

    def _update_professional_panels(self, data: DashboardData) -> None:
        self._update_milestones(data)
        self._update_watchlist(data)

    def _update_milestones(self, data: DashboardData) -> None:
        rows = getattr(data, "milestone_health", []) or []
        self.milestone_group.setTitle(f"Milestone Health ({len(rows)})")
        self.milestone_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            values = [
                item.task_name,
                item.target_date.isoformat() if item.target_date else "-",
                item.owner_name or "-",
                item.status_label,
                f"{int(item.slip_days)}d" if item.slip_days is not None else "-",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 4:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 3:
                    cell.setForeground(QColor(self._status_color(item.status_label)))
                if col == 4 and item.slip_days is not None and int(item.slip_days) > 0:
                    cell.setForeground(QColor(CFG.COLOR_DANGER))
                self.milestone_table.setItem(row_idx, col, cell)

    def _update_watchlist(self, data: DashboardData) -> None:
        rows = getattr(data, "critical_watchlist", []) or []
        self.watchlist_group.setTitle(f"Critical Path Watchlist ({len(rows)})")
        self.watchlist_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            values = [
                item.task_name,
                item.finish_date.isoformat() if item.finish_date else "-",
                item.owner_name or "-",
                str(int(item.total_float_days or 0)) if item.total_float_days is not None else "-",
                item.status_label,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 3:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 4:
                    cell.setForeground(QColor(self._status_color(item.status_label)))
                self.watchlist_table.setItem(row_idx, col, cell)

    @staticmethod
    def _status_color(status_label: str) -> str:
        label = str(status_label or "").strip().lower()
        if label in {"late", "blocked"}:
            return CFG.COLOR_DANGER
        if label in {"due soon", "critical"}:
            return CFG.COLOR_WARNING
        if label == "done":
            return CFG.COLOR_SUCCESS
        return CFG.COLOR_ACCENT


__all__ = ["DashboardProfessionalRenderingMixin"]
