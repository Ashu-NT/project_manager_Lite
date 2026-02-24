from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ui.dashboard.styles import dashboard_action_button_style
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class DashboardAlertsPanelMixin:
    alerts_status: QLabel
    btn_preview_conflicts: QPushButton
    btn_auto_level: QPushButton
    btn_manual_shift: QPushButton
    alerts_table: QTableWidget
    conflicts_table: QTableWidget

    def _build_alerts_panel(self) -> QGroupBox:
        alerts_group = QGroupBox("Alerts")
        alerts_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        alerts_layout = QVBoxLayout(alerts_group)
        alerts_layout.setContentsMargins(
            CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM
        )
        alerts_layout.setSpacing(CFG.SPACING_SM)

        alerts_head = QHBoxLayout()
        alerts_head.setContentsMargins(0, 0, 0, 0)
        alerts_head.setSpacing(CFG.SPACING_SM)
        self.alerts_status = QLabel("0 active alerts")
        self.alerts_status.setWordWrap(True)
        self.alerts_status.setMinimumHeight(34)
        self.alerts_status.setStyleSheet(
            f"""
            font-weight: 700;
            color: {CFG.COLOR_TEXT_PRIMARY};
            font-size: 10pt;
            background-color: {CFG.COLOR_BG_SURFACE_ALT};
            border: 1px solid {CFG.COLOR_BORDER};
            border-radius: 8px;
            padding: 6px 8px;
            """
        )
        alerts_head.addWidget(self.alerts_status, 1)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(CFG.SPACING_XS)

        self.btn_preview_conflicts = QPushButton("Preview Conflicts")
        self.btn_auto_level = QPushButton("Auto-Level")
        self.btn_manual_shift = QPushButton("Manual Shift")
        self.btn_preview_conflicts.setToolTip(
            "Analyze daily resource over-allocation conflicts for this project."
        )
        self.btn_auto_level.setToolTip(
            "Automatically shift eligible tasks to reduce over-allocation conflicts."
        )
        self.btn_manual_shift.setToolTip(
            "Select a conflict row, then shift one task by working days (safe tasks only)."
        )
        for btn in (self.btn_preview_conflicts, self.btn_auto_level, self.btn_manual_shift):
            btn.setSizePolicy(CFG.H_EXPAND_V_FIXED)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setMinimumWidth(128)
        self.btn_preview_conflicts.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_auto_level.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_manual_shift.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_auto_level.setEnabled(False)
        self.btn_manual_shift.setEnabled(False)

        actions_row.addWidget(self.btn_preview_conflicts)
        actions_row.addWidget(self.btn_auto_level)
        actions_row.addWidget(self.btn_manual_shift)
        alerts_layout.addLayout(alerts_head)
        alerts_layout.addLayout(actions_row)

        self.alerts_table = QTableWidget(0, 3)
        self.alerts_table.setHorizontalHeaderLabels(["Severity", "Issue", "Recommended Action"])
        style_table(self.alerts_table)
        self.alerts_table.setWordWrap(True)
        self.alerts_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        a_header = self.alerts_table.horizontalHeader()
        a_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        a_header.setSectionResizeMode(1, QHeaderView.Stretch)
        a_header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.alerts_table.setMinimumHeight(110)
        alerts_layout.addWidget(self.alerts_table)

        conflicts_lbl = QLabel("Resource conflicts (daily overload)")
        conflicts_lbl.setStyleSheet(
            f"font-weight: 600; color: {CFG.COLOR_TEXT_SECONDARY};"
        )
        alerts_layout.addWidget(conflicts_lbl)
        self.conflicts_table = QTableWidget(0, 4)
        self.conflicts_table.setHorizontalHeaderLabels(["Resource", "Date", "Load %", "Tasks"])
        style_table(self.conflicts_table)
        self.conflicts_table.setWordWrap(True)
        c_header = self.conflicts_table.horizontalHeader()
        c_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.conflicts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.conflicts_table.setSelectionMode(QTableWidget.SingleSelection)
        self.conflicts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.conflicts_table.setMinimumHeight(120)
        alerts_layout.addWidget(self.conflicts_table)

        self.conflicts_table.setRowCount(1)
        for col in range(4):
            item = QTableWidgetItem("-")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self.conflicts_table.setItem(0, col, item)

        return alerts_group


__all__ = ["DashboardAlertsPanelMixin"]
