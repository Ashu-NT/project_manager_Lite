from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QHeaderView, QTableWidget, QVBoxLayout

from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class DashboardPortfolioPanelMixin:
    def _build_portfolio_panel(self):
        box = QGroupBox("Portfolio Ranking")
        box.setFont(CFG.GROUPBOX_TITLE_FONT)

        self.portfolio_table = QTableWidget(0, 6)
        self.portfolio_table.setHorizontalHeaderLabels(
            ["Project", "Status", "Progress", "Late", "Critical", "Cost Var"]
        )
        self.portfolio_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.portfolio_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.portfolio_table.setSelectionMode(QTableWidget.SingleSelection)
        style_table(self.portfolio_table)

        header = self.portfolio_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.portfolio_table.verticalHeader().setVisible(False)
        self.portfolio_table.setMinimumHeight(220)

        root = QVBoxLayout(box)
        root.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        root.setSpacing(CFG.SPACING_SM)
        root.addWidget(self.portfolio_table)
        return box


__all__ = ["DashboardPortfolioPanelMixin"]
