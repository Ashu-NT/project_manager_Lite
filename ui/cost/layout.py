from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableView,
    QTableWidget,
    QVBoxLayout,
)

from ui.cost.models import CostTableModel
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class CostLayoutMixin:
    table: QTableView
    model: CostTableModel
    filter_text: QLineEdit
    filter_type_combo: QComboBox
    filter_task_combo: QComboBox
    btn_clear_filters: QPushButton
    lbl_costs_summary: QLabel
    tbl_labor_summary: QTableWidget
    btn_labor_details: QPushButton
    lbl_labor_note: QLabel

    def _build_cost_items_group(self) -> QGroupBox:
        grp_costs = QGroupBox("Cost Items")
        grp_costs.setFont(CFG.GROUPBOX_TITLE_FONT)
        costs_layout = QVBoxLayout(grp_costs)
        costs_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        costs_layout.setSpacing(CFG.SPACING_SM)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(CFG.SPACING_SM)
        self.filter_text = QLineEdit()
        self.filter_text.setPlaceholderText("Filter by description or task")
        self.filter_text.setFixedHeight(CFG.INPUT_HEIGHT)
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.filter_type_combo.addItem("All Types", userData="")
        self.filter_task_combo = QComboBox()
        self.filter_task_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.filter_task_combo.addItem("All Tasks", userData="")
        self.btn_clear_filters = QPushButton("Clear Filters")
        self.btn_clear_filters.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_clear_filters.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        filter_row.addWidget(self.filter_text, 1)
        filter_row.addWidget(self.filter_type_combo)
        filter_row.addWidget(self.filter_task_combo)
        filter_row.addWidget(self.btn_clear_filters)
        costs_layout.addLayout(filter_row)

        self.lbl_costs_summary = QLabel("")
        self.lbl_costs_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.lbl_costs_summary.setWordWrap(True)
        costs_layout.addWidget(self.lbl_costs_summary)

        self.table = QTableView()
        self.model = CostTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        costs_layout.addWidget(self.table)
        return grp_costs

    def _build_labor_group(self) -> QGroupBox:
        grp_labor = QGroupBox("Labor Snapshot")
        grp_labor.setFont(CFG.GROUPBOX_TITLE_FONT)
        labor_layout = QVBoxLayout(grp_labor)
        labor_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        labor_layout.setSpacing(CFG.SPACING_MD)

        self.tbl_labor_summary = QTableWidget()
        self.tbl_labor_summary.setColumnCount(len(CFG.LABOR_SUMMARY_HEADERS))
        self.tbl_labor_summary.setHorizontalHeaderLabels(CFG.LABOR_SUMMARY_HEADERS)
        self.tbl_labor_summary.verticalHeader().setVisible(False)
        self.tbl_labor_summary.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_labor_summary.setSelectionMode(QTableWidget.NoSelection)
        self.tbl_labor_summary.horizontalHeader().setStretchLastSection(True)
        self.tbl_labor_summary.setMinimumHeight(160)
        self.tbl_labor_summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        style_table(self.tbl_labor_summary)
        labor_layout.addWidget(self.tbl_labor_summary, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, CFG.SPACING_XS, 0, 0)
        button_row.setSpacing(CFG.SPACING_SM)
        button_row.addStretch()
        self.btn_labor_details = QPushButton(CFG.LABOR_DETAILS_BUTTON_LABEL)
        self.btn_labor_details.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_labor_details.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_labor_details.setToolTip("Open detailed labor usage and cost breakdown by resource.")
        button_row.addWidget(self.btn_labor_details)
        labor_layout.addLayout(button_row)

        self.lbl_labor_note = QLabel("")
        self.lbl_labor_note.setWordWrap(True)
        self.lbl_labor_note.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        labor_layout.addWidget(self.lbl_labor_note)
        return grp_labor


__all__ = ["CostLayoutMixin"]
