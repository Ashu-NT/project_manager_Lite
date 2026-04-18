from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QHeaderView, QTableWidget, QVBoxLayout

from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG


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

    def _build_register_panel(self):
        box = QGroupBox("Risk / Issue / Change Summary")
        box.setFont(CFG.GROUPBOX_TITLE_FONT)
        root = QVBoxLayout(box)
        root.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        root.setSpacing(CFG.SPACING_SM)

        self.register_summary_label = QTableWidget(0, 2)
        self.register_summary_label.setHorizontalHeaderLabels(["Signal", "Count"])
        self.register_summary_label.setEditTriggers(QTableWidget.NoEditTriggers)
        self.register_summary_label.setSelectionBehavior(QTableWidget.SelectRows)
        self.register_summary_label.setSelectionMode(QTableWidget.NoSelection)
        style_table(self.register_summary_label)
        summary_header = self.register_summary_label.horizontalHeader()
        summary_header.setSectionResizeMode(0, QHeaderView.Stretch)
        summary_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.register_summary_label.verticalHeader().setVisible(False)
        self.register_summary_label.setMinimumHeight(170)

        self.register_urgent_table = QTableWidget(0, 5)
        self.register_urgent_table.setHorizontalHeaderLabels(["Type", "Title", "Severity", "Owner", "Due"])
        self.register_urgent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.register_urgent_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.register_urgent_table.setSelectionMode(QTableWidget.SingleSelection)
        style_table(self.register_urgent_table)
        urgent_header = self.register_urgent_table.horizontalHeader()
        urgent_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        urgent_header.setSectionResizeMode(1, QHeaderView.Stretch)
        urgent_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        urgent_header.setSectionResizeMode(3, QHeaderView.Stretch)
        urgent_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.register_urgent_table.verticalHeader().setVisible(False)
        self.register_urgent_table.setMinimumHeight(220)

        root.addWidget(self.register_summary_label)
        root.addWidget(self.register_urgent_table)
        return box


__all__ = ["DashboardProfessionalPanelMixin"]
