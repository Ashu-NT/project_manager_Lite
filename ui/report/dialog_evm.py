from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.services.reporting import ReportingService
from ui.report.dialog_helpers import metric_card, setup_dialog_size
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f}"


def _fmt_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"


class EvmReportDialog(QDialog):
    def __init__(
        self,
        parent,
        reporting_service: ReportingService,
        project_id: str,
        project_name: str,
        as_of: date | None = None,
    ):
        super().__init__(parent)
        self._reporting_service: ReportingService = reporting_service
        self._project_id: str = project_id
        self._project_name: str = project_name
        self._as_of: date = as_of or date.today()
        self.setWindowTitle(f"EVM Analysis - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        evm = self._reporting_service.get_earned_value(self._project_id, as_of=self._as_of)
        series = self._reporting_service.get_evm_series(self._project_id, as_of=self._as_of)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        setup_dialog_size(self, 980, 620, 1180, 760)

        title = QLabel(f"Earned Value Management - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        subtitle = QLabel(
            f"As of: {self._as_of.isoformat()} | Baseline: {evm.baseline_id}\n"
            "Use CPI/SPI for performance trend and EAC/VAC for forecast at completion."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(subtitle)

        cards_1 = QHBoxLayout()
        cards_1.setSpacing(CFG.SPACING_SM)
        cards_1.addWidget(metric_card("BAC", _fmt_money(evm.BAC), "Baseline at completion", CFG.COLOR_ACCENT))
        cards_1.addWidget(metric_card("PV", _fmt_money(evm.PV), "Planned value", CFG.COLOR_WARNING))
        cards_1.addWidget(metric_card("EV", _fmt_money(evm.EV), "Earned value", CFG.COLOR_SUCCESS))
        cards_1.addWidget(metric_card("AC", _fmt_money(evm.AC), "Actual cost", CFG.COLOR_DANGER))
        layout.addLayout(cards_1)

        cpi_color = CFG.COLOR_SUCCESS if (evm.CPI or 0.0) >= 1.0 else CFG.COLOR_DANGER
        spi_color = CFG.COLOR_SUCCESS if (evm.SPI or 0.0) >= 1.0 else CFG.COLOR_DANGER
        vac_color = CFG.COLOR_SUCCESS if (evm.VAC or 0.0) >= 0.0 else CFG.COLOR_DANGER
        cards_2 = QHBoxLayout()
        cards_2.setSpacing(CFG.SPACING_SM)
        cards_2.addWidget(metric_card("CPI", _fmt_ratio(evm.CPI), "Cost performance", cpi_color))
        cards_2.addWidget(metric_card("SPI", _fmt_ratio(evm.SPI), "Schedule performance", spi_color))
        cards_2.addWidget(metric_card("EAC", _fmt_money(evm.EAC), "Estimate at completion", CFG.COLOR_TEXT_SECONDARY))
        cards_2.addWidget(metric_card("VAC", _fmt_money(evm.VAC), "Variance at completion", vac_color))
        layout.addLayout(cards_2)

        notes = QLabel(evm.notes or "No calculation notes.")
        notes.setWordWrap(True)
        notes.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        layout.addWidget(notes)

        table = QTableWidget(len(series), 7)
        table.setHorizontalHeaderLabels(["Period End", "PV", "EV", "AC", "CPI", "SPI", "BAC"])
        style_table(table)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in (1, 2, 3, 6):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        for col in (4, 5):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(False)

        for row, point in enumerate(series):
            table.setItem(row, 0, QTableWidgetItem(point.period_end.isoformat()))
            for col, value in [
                (1, _fmt_money(point.PV)),
                (2, _fmt_money(point.EV)),
                (3, _fmt_money(point.AC)),
                (4, _fmt_ratio(point.CPI)),
                (5, _fmt_ratio(point.SPI)),
                (6, _fmt_money(point.BAC)),
            ]:
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row, col, item)
        layout.addWidget(table)

        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setFixedHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)


__all__ = ["EvmReportDialog"]

