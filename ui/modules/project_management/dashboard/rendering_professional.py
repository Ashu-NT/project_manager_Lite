from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGroupBox, QTableWidget, QTableWidgetItem

from src.core.modules.project_management.domain.risk.register import as_register_entry_severity, as_register_entry_type
from core.modules.project_management.services.dashboard import DashboardData
from src.core.modules.project_management.application.risk import RegisterProjectSummary
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class DashboardProfessionalRenderingMixin:
    milestone_group: QGroupBox
    milestone_table: QTableWidget
    watchlist_group: QGroupBox
    watchlist_table: QTableWidget
    register_group: QGroupBox
    register_summary_label: QTableWidget
    register_urgent_table: QTableWidget

    def _clear_professional_panels(self) -> None:
        if hasattr(self, "milestone_table"):
            self.milestone_table.setRowCount(0)
        if hasattr(self, "watchlist_table"):
            self.watchlist_table.setRowCount(0)
        if hasattr(self, "register_summary_label"):
            self.register_summary_label.setRowCount(0)
        if hasattr(self, "register_urgent_table"):
            self.register_urgent_table.setRowCount(0)
        if hasattr(self, "milestone_group"):
            self.milestone_group.setTitle("Milestone Health")
        if hasattr(self, "watchlist_group"):
            self.watchlist_group.setTitle("Critical Path Watchlist")
        if hasattr(self, "register_group"):
            self.register_group.setTitle("Risk / Issue / Change Summary")

    def _update_professional_panels(self, data: DashboardData) -> None:
        self._update_milestones(data)
        self._update_watchlist(data)
        self._update_register_summary(getattr(data, "register_summary", None))

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

    def _update_register_summary(self, summary: RegisterProjectSummary | None) -> None:
        if summary is None:
            self.register_group.setTitle("Risk / Issue / Change Summary")
            self.register_summary_label.setRowCount(0)
            self.register_urgent_table.setRowCount(0)
            return
        signals = [
            ("Open risks", summary.open_risks),
            ("Open issues", summary.open_issues),
            ("Pending changes", summary.pending_changes),
            ("Overdue items", summary.overdue_items),
            ("Critical items", summary.critical_items),
        ]
        total = sum(count for _, count in signals)
        self.register_group.setTitle(f"Risk / Issue / Change Summary ({total})")
        self.register_summary_label.setRowCount(len(signals))
        for row_idx, (label, count) in enumerate(signals):
            label_item = QTableWidgetItem(label)
            count_item = QTableWidgetItem(str(int(count)))
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if label in {"Overdue items", "Critical items"} and int(count) > 0:
                count_item.setForeground(QColor(CFG.COLOR_DANGER))
            self.register_summary_label.setItem(row_idx, 0, label_item)
            self.register_summary_label.setItem(row_idx, 1, count_item)
        self.register_urgent_table.setRowCount(len(summary.urgent_items))
        for row_idx, item in enumerate(summary.urgent_items):
            values = [
                as_register_entry_type(item.entry_type).value.title(),
                item.title,
                as_register_entry_severity(item.severity).value.title(),
                item.owner_name or "-",
                item.due_date.isoformat() if item.due_date else "-",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 2:
                    cell.setForeground(QColor(self._severity_color(as_register_entry_severity(item.severity).value)))
                self.register_urgent_table.setItem(row_idx, col, cell)

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

    @staticmethod
    def _severity_color(label: str) -> str:
        normalized = str(label or "").strip().lower()
        if normalized == "critical":
            return CFG.COLOR_DANGER
        if normalized == "high":
            return CFG.COLOR_WARNING
        return CFG.COLOR_ACCENT


__all__ = ["DashboardProfessionalRenderingMixin"]
