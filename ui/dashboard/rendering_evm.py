from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from core.services.dashboard import DashboardData
from ui.dashboard.evm_rows import build_metric_row, build_status_row
from ui.styles.formatting import fmt_money, fmt_ratio
from ui.styles.ui_config import UIConfig as CFG


class DashboardEvmRenderingMixin:
    baseline_combo: QComboBox
    evm_hint: QLabel
    evm_cost_summary: QLabel
    evm_schedule_summary: QLabel
    evm_forecast_summary: QLabel
    evm_TCPI_summary: QLabel
    lbl_cpi: QLabel
    lbl_spi: QLabel
    lbl_eac: QLabel
    lbl_vac: QLabel
    lbl_pv: QLabel
    lbl_ev: QLabel
    lbl_ac: QLabel
    lbl_tcpi: QLabel
    lbl_tcpi_eac: QLabel

    def _build_evm_panel(self):
        box = QGroupBox("Earned Value (EVM)")
        box.setFont(CFG.GROUPBOX_TITLE_FONT)
        root = QVBoxLayout(box)
        root.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        root.setSpacing(CFG.SPACING_SM)
        self.evm_hint = QLabel("Create a baseline to enable EVM metrics.")
        self.evm_hint.setWordWrap(True)
        self.evm_hint.setMinimumHeight(34)
        self.evm_hint.setStyleSheet(
            f"""
            color: {CFG.COLOR_TEXT_SECONDARY};
            background-color: {CFG.COLOR_BG_SURFACE_ALT};
            border: 1px solid {CFG.COLOR_BORDER};
            border-radius: 8px;
            padding: 6px 10px;
            """
        )
        root.addWidget(self.evm_hint)

        self.lbl_cpi = QLabel("-")
        self.lbl_spi = QLabel("-")
        self.lbl_eac = QLabel("-")
        self.lbl_vac = QLabel("-")
        self.lbl_pv = QLabel("-")
        self.lbl_ev = QLabel("-")
        self.lbl_ac = QLabel("-")
        self.lbl_tcpi = QLabel("-")
        self.lbl_tcpi_eac = QLabel("-")
        self.evm_cost_summary = QLabel("")
        self.evm_schedule_summary = QLabel("")
        self.evm_forecast_summary = QLabel("")
        self.evm_TCPI_summary = QLabel("")
        summary_rows = [
            (self.evm_cost_summary, CFG.COLOR_DANGER),
            (self.evm_schedule_summary, CFG.COLOR_SUCCESS),
            (self.evm_forecast_summary, CFG.COLOR_WARNING),
            (self.evm_TCPI_summary, CFG.COLOR_TEXT_SECONDARY),
        ]
        summary_layout = QVBoxLayout()
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(CFG.SPACING_XS)
        for lbl, accent in summary_rows:
            row = build_status_row(lbl, accent)
            summary_layout.addWidget(row)
        summary_host = QWidget()
        summary_host.setLayout(summary_layout)
        root.addWidget(summary_host)

        self.cpi_lbl = QLabel("CPI")
        self.pv_lbl = QLabel("PV")
        self.spi_lbl = QLabel("SPI")
        self.ev_lbl = QLabel("EV")
        self.eac_lbl = QLabel("EAC")
        self.ac_lbl = QLabel("AC")
        self.tcpi_bac = QLabel("TCPI(BAC)")
        self.vac_lbl = QLabel("VAC")
        self.tcpi_eac = QLabel("TCPI(EAC)")

        evm_map = getattr(CFG, "EVM_METRIC_COLORS", {})
        metrics = [
            (self.cpi_lbl, self.lbl_cpi, "CPI"),
            (self.spi_lbl, self.lbl_spi, "SPI"),
            (self.pv_lbl, self.lbl_pv, "PV"),
            (self.ev_lbl, self.lbl_ev, "EV"),
            (self.ac_lbl, self.lbl_ac, "AC"),
            (self.eac_lbl, self.lbl_eac, "EAC"),
            (self.vac_lbl, self.lbl_vac, "VAC"),
            (self.tcpi_bac, self.lbl_tcpi, "TCPI"),
            (self.tcpi_eac, self.lbl_tcpi_eac, "TCPI_EAC"),
        ]

        metrics_grid = QGridLayout()
        metrics_grid.setContentsMargins(0, 0, 0, 0)
        metrics_grid.setHorizontalSpacing(CFG.SPACING_XS)
        metrics_grid.setVerticalSpacing(CFG.SPACING_XS)
        for i in range(3):
            metrics_grid.setColumnStretch(i, 1)
        for index, (title_label, value_label, metric_key) in enumerate(metrics):
            row = index // 3
            col = index % 3
            color = evm_map.get(metric_key, CFG.EVM_DEFAULT_COLOR)
            metrics_grid.addWidget(build_metric_row(title_label, value_label, color), row, col)
        metrics_host = QWidget()
        metrics_host.setLayout(metrics_grid)
        metrics_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        root.addWidget(metrics_host)

        box.setStyleSheet(
            f"""
            QGroupBox {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border-radius: 10px;
                border: 1px solid {CFG.COLOR_BORDER};
                margin-top: 8px;
            }}
            QGroupBox:title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: {CFG.COLOR_TEXT_SECONDARY};
                font-weight: bold;
            }}
        """
        )
        return box

    def _format_evm_part(self, heading: str, text: str) -> str:
        clean = " ".join((text or "").split())
        if not clean:
            return f"{heading}: -"
        if ":" in clean:
            return clean
        return f"{heading}: {clean}"

    def _reset_evm_view(self) -> None:
        if hasattr(self, "evm_hint"):
            self.evm_hint.setText("Create a baseline to enable EVM metrics.")
        if hasattr(self, "evm_cost_summary"):
            self.evm_cost_summary.setText("Cost: -")
            self.evm_schedule_summary.setText("Schedule: -")
            self.evm_forecast_summary.setText("Forecast: -")
            self.evm_TCPI_summary.setText("TCPI: -")
        self.lbl_cpi.setText("-")
        self.lbl_spi.setText("-")
        self.lbl_eac.setText("-")
        self.lbl_vac.setText("-")
        self.lbl_pv.setText("-")
        self.lbl_ev.setText("-")
        self.lbl_ac.setText("-")
        self.lbl_tcpi.setText("-")
        self.lbl_tcpi_eac.setText("-")

    def _update_evm(self, data: DashboardData):
        if data.evm is None:
            self._reset_evm_view()
            return
        evm = data.evm
        selected_id = self._selected_baseline_id()
        baseline_label = self.baseline_combo.currentText() if selected_id else "Latest baseline"
        self.evm_hint.setText(f"As of {evm.as_of.isoformat()} (baseline: {baseline_label})")

        self.lbl_cpi.setText(fmt_ratio(evm.CPI))
        self.lbl_spi.setText(fmt_ratio(evm.SPI))
        self.lbl_eac.setText(fmt_money(evm.EAC))
        self.lbl_vac.setText(fmt_money(evm.VAC))
        self.lbl_pv.setText(fmt_money(evm.PV))
        self.lbl_ev.setText(fmt_money(evm.EV))
        self.lbl_ac.setText(fmt_money(evm.AC))
        self.lbl_tcpi.setText(fmt_ratio(evm.TCPI_to_BAC))
        self.lbl_tcpi_eac.setText(fmt_ratio(evm.TCPI_to_EAC))

        parts = [p.strip() for p in (evm.status_text or "").split(".") if p.strip()]
        p0 = parts[0] if len(parts) > 0 else ""
        p1 = parts[1] if len(parts) > 1 else ""
        p2 = parts[2] if len(parts) > 2 else ""
        p3 = parts[3] if len(parts) > 3 else ""

        self.evm_cost_summary.setText(self._format_evm_part("Cost", p0))
        self.evm_schedule_summary.setText(self._format_evm_part("Schedule", p1))
        self.evm_forecast_summary.setText(self._format_evm_part("Forecast", p2))
        self.evm_TCPI_summary.setText(self._format_evm_part("TCPI", p3))
