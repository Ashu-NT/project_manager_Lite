from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGroupBox, QTableWidget, QTableWidgetItem

from core.services.dashboard import DashboardData
from ui.styles.formatting import fmt_float, fmt_percent
from ui.styles.ui_config import UIConfig as CFG


class DashboardPortfolioRenderingMixin:
    portfolio_group: QGroupBox
    portfolio_table: QTableWidget

    def _clear_portfolio_panel(self) -> None:
        if not hasattr(self, "portfolio_group"):
            return
        self.portfolio_table.setRowCount(0)
        self.portfolio_group.setHidden(True)

    def _update_portfolio_panel(self, data: DashboardData) -> None:
        portfolio = getattr(data, "portfolio", None)
        if not hasattr(self, "portfolio_group"):
            return
        if portfolio is None:
            self._clear_portfolio_panel()
            return

        rows = portfolio.project_rankings
        self.portfolio_group.setHidden(False)
        self.portfolio_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = [
                item.project_name,
                item.project_status.replace("_", " "),
                fmt_percent(item.progress_percent, 1),
                str(int(item.late_tasks or 0)),
                str(int(item.critical_tasks or 0)),
                fmt_float(item.cost_variance, 2),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col in {2, 3, 4, 5}:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 1 and item.project_status == "ON_HOLD":
                    cell.setForeground(QColor(CFG.COLOR_WARNING))
                if col == 5 and float(item.cost_variance or 0.0) > 0.0:
                    cell.setForeground(QColor(CFG.COLOR_DANGER))
                self.portfolio_table.setItem(row, col, cell)


__all__ = ["DashboardPortfolioRenderingMixin"]
