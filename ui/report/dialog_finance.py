from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.services.finance import FinanceAnalyticsRow, FinanceService, FinanceSnapshot
from ui.report.dialog_helpers import setup_dialog_size
from ui.styles.formatting import currency_symbol_from_code, fmt_currency
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class FinanceReportDialog(QDialog):
    def __init__(
        self,
        parent,
        finance_service: FinanceService,
        project_id: str,
        project_name: str,
    ) -> None:
        super().__init__(parent)
        self._finance_service = finance_service
        self._project_id = project_id
        self._project_name = project_name
        self._snapshot: FinanceSnapshot | None = None
        self.setWindowTitle(f"Finance Report - {project_name}")
        self._setup_ui()
        self._reload_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_SM)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        setup_dialog_size(self, 1080, 680, 1260, 820)

        title = QLabel(f"Finance Report - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        subtitle = QLabel(
            "Policy-aligned commercial view: ledger trail, period cashflow/forecast, and expense analytics."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        controls = QHBoxLayout()
        controls.setSpacing(CFG.SPACING_SM)
        controls.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.period_combo.addItem("Monthly", userData="month")
        self.period_combo.addItem("Weekly", userData="week")
        controls.addWidget(self.period_combo)

        controls.addWidget(QLabel("Analytics:"))
        self.dimension_combo = QComboBox()
        self.dimension_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.dimension_combo.addItem("By Source", userData="source")
        self.dimension_combo.addItem("By Cost Type", userData="cost_type")
        self.dimension_combo.addItem("By Resource", userData="resource")
        self.dimension_combo.addItem("By Task", userData="task")
        controls.addWidget(self.dimension_combo)
        controls.addStretch()

        self.btn_refresh = QPushButton("Refresh Finance")
        self.btn_refresh.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_refresh.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        controls.addWidget(self.btn_refresh)
        layout.addLayout(controls)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.lbl_summary.setWordWrap(True)
        layout.addWidget(self.lbl_summary)

        grp_cash = QGroupBox("Cashflow / Forecast by Period")
        grp_cash.setFont(CFG.GROUPBOX_TITLE_FONT)
        cash_layout = QVBoxLayout(grp_cash)
        self.tbl_cashflow = QTableWidget(0, 6)
        self.tbl_cashflow.setHorizontalHeaderLabels(
            ["Period", "Planned", "Committed", "Actual", "Forecast", "Exposure"]
        )
        style_table(self.tbl_cashflow)
        cash_layout.addWidget(self.tbl_cashflow)

        grp_analytics = QGroupBox("Expense Analytics")
        grp_analytics.setFont(CFG.GROUPBOX_TITLE_FONT)
        analytics_layout = QVBoxLayout(grp_analytics)
        self.tbl_analytics = QTableWidget(0, 6)
        self.tbl_analytics.setHorizontalHeaderLabels(
            ["Category", "Planned", "Committed", "Actual", "Forecast", "Exposure"]
        )
        style_table(self.tbl_analytics)
        analytics_layout.addWidget(self.tbl_analytics)

        grp_ledger = QGroupBox("Ledger Trail")
        grp_ledger.setFont(CFG.GROUPBOX_TITLE_FONT)
        ledger_layout = QVBoxLayout(grp_ledger)
        self.tbl_ledger = QTableWidget(0, 9)
        self.tbl_ledger.setHorizontalHeaderLabels(
            ["Date", "Source", "Stage", "Type", "Reference", "Task", "Resource", "Amount", "In Policy"]
        )
        style_table(self.tbl_ledger)
        ledger_layout.addWidget(self.tbl_ledger)

        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.addWidget(grp_cash)
        self.main_splitter.addWidget(grp_analytics)
        self.main_splitter.addWidget(grp_ledger)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 2)
        self.main_splitter.setSizes([220, 220, 360])
        layout.addWidget(self.main_splitter, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setFixedHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self.period_combo.currentIndexChanged.connect(self._reload_data)
        self.dimension_combo.currentIndexChanged.connect(self._refresh_analytics_only)
        self.btn_refresh.clicked.connect(self._reload_data)

    def _reload_data(self, *_args) -> None:
        period = str(self.period_combo.currentData() or "month")
        self._snapshot = self._finance_service.get_finance_snapshot(
            self._project_id,
            period=period,
        )
        self._refresh_views()

    def _refresh_analytics_only(self, *_args) -> None:
        if self._snapshot is None:
            return
        self._populate_analytics(
            self._analytics_rows(),
            currency_symbol_from_code(self._snapshot.project_currency),
        )

    def _refresh_views(self) -> None:
        if self._snapshot is None:
            return
        sym = currency_symbol_from_code(self._snapshot.project_currency)
        available = (
            "-"
            if self._snapshot.available is None
            else fmt_currency(self._snapshot.available, sym)
        )
        self.lbl_summary.setText(
            "Budget {budget} | Planned {planned} | Committed {committed} | "
            "Actual {actual} | Exposure {exposure} | Available {available}".format(
                budget=fmt_currency(self._snapshot.budget, sym),
                planned=fmt_currency(self._snapshot.planned, sym),
                committed=fmt_currency(self._snapshot.committed, sym),
                actual=fmt_currency(self._snapshot.actual, sym),
                exposure=fmt_currency(self._snapshot.exposure, sym),
                available=available,
            )
        )
        self._populate_cashflow(sym)
        self._populate_analytics(self._analytics_rows(), sym)
        self._populate_ledger(sym)

    def _analytics_rows(self) -> list[FinanceAnalyticsRow]:
        if self._snapshot is None:
            return []
        mode = str(self.dimension_combo.currentData() or "source")
        if mode == "cost_type":
            return self._snapshot.by_cost_type
        if mode == "resource":
            return self._snapshot.by_resource
        if mode == "task":
            return self._snapshot.by_task
        return self._snapshot.by_source

    def _populate_cashflow(self, sym: str) -> None:
        assert self._snapshot is not None
        self.tbl_cashflow.setRowCount(len(self._snapshot.cashflow))
        for i, row in enumerate(self._snapshot.cashflow):
            self._set_cell(self.tbl_cashflow, i, 0, row.period_key)
            self._set_cell(self.tbl_cashflow, i, 1, fmt_currency(row.planned, sym), align_right=True)
            self._set_cell(self.tbl_cashflow, i, 2, fmt_currency(row.committed, sym), align_right=True)
            self._set_cell(self.tbl_cashflow, i, 3, fmt_currency(row.actual, sym), align_right=True)
            self._set_cell(self.tbl_cashflow, i, 4, fmt_currency(row.forecast, sym), align_right=True)
            self._set_cell(self.tbl_cashflow, i, 5, fmt_currency(row.exposure, sym), align_right=True)

    def _populate_analytics(self, rows: list[FinanceAnalyticsRow], sym: str) -> None:
        self.tbl_analytics.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self._set_cell(self.tbl_analytics, i, 0, row.label)
            self._set_cell(self.tbl_analytics, i, 1, fmt_currency(row.planned, sym), align_right=True)
            self._set_cell(self.tbl_analytics, i, 2, fmt_currency(row.committed, sym), align_right=True)
            self._set_cell(self.tbl_analytics, i, 3, fmt_currency(row.actual, sym), align_right=True)
            self._set_cell(self.tbl_analytics, i, 4, fmt_currency(row.forecast, sym), align_right=True)
            self._set_cell(self.tbl_analytics, i, 5, fmt_currency(row.exposure, sym), align_right=True)

    def _populate_ledger(self, sym: str) -> None:
        assert self._snapshot is not None
        self.tbl_ledger.setRowCount(len(self._snapshot.ledger))
        for i, row in enumerate(self._snapshot.ledger):
            self._set_cell(self.tbl_ledger, i, 0, row.occurred_on.isoformat() if row.occurred_on else "-")
            self._set_cell(self.tbl_ledger, i, 1, row.source_label)
            self._set_cell(self.tbl_ledger, i, 2, row.stage.title())
            self._set_cell(self.tbl_ledger, i, 3, row.cost_type)
            self._set_cell(self.tbl_ledger, i, 4, row.reference_label)
            self._set_cell(self.tbl_ledger, i, 5, row.task_name or "-")
            self._set_cell(self.tbl_ledger, i, 6, row.resource_name or "-")
            self._set_cell(self.tbl_ledger, i, 7, fmt_currency(row.amount, sym), align_right=True)
            self._set_cell(
                self.tbl_ledger,
                i,
                8,
                "Yes" if row.included_in_policy else "No",
                align_right=False,
            )

    @staticmethod
    def _set_cell(
        table: QTableWidget,
        row: int,
        col: int,
        text: str,
        *,
        align_right: bool = False,
    ) -> None:
        item = QTableWidgetItem(text)
        if align_right:
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.setItem(row, col, item)


__all__ = ["FinanceReportDialog"]
