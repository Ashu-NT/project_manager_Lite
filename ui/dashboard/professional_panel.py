from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QHeaderView, QTableWidget, QVBoxLayout

from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class DashboardProfessionalPanelMixin:
    def _build_milestone_panel(self):
        box = QGroupBox("Milestone Health")
        box.setFont(CFG.GROUPBOX_TITLE_FONT)
        self.milestone_table = QTableWidget(0, 5)
        self.milestone_table.setHorizontalHeaderLabels(["Milestone", "Target", "Owner", "Status", "Slip"])
        self.milestone_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.milestone_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.milestone_table.setSelectionMode(QTableWidget.SingleSelection)
        style_table(self.milestone_table)
        header = self.milestone_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.milestone_table.verticalHeader().setVisible(False)
        self.milestone_table.setMinimumHeight(220)

        root = QVBoxLayout(box)
        root.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        root.setSpacing(CFG.SPACING_SM)
        root.addWidget(self.milestone_table)
        return box

    def _build_watchlist_panel(self):
        box = QGroupBox("Critical Path Watchlist")
        box.setFont(CFG.GROUPBOX_TITLE_FONT)
        self.watchlist_table = QTableWidget(0, 5)
        self.watchlist_table.setHorizontalHeaderLabels(["Task", "Finish", "Owner", "Float", "Status"])
        self.watchlist_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.watchlist_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.watchlist_table.setSelectionMode(QTableWidget.SingleSelection)
        style_table(self.watchlist_table)
        header = self.watchlist_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.watchlist_table.verticalHeader().setVisible(False)
        self.watchlist_table.setMinimumHeight(220)

        root = QVBoxLayout(box)
        root.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        root.setSpacing(CFG.SPACING_SM)
        root.addWidget(self.watchlist_table)
        return box


__all__ = ["DashboardProfessionalPanelMixin"]
