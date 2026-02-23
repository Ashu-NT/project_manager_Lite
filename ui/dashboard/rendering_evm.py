from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QGroupBox, QLabel

from core.services.dashboard import DashboardData
from ui.styles.formatting import fmt_money, fmt_ratio
from ui.styles.ui_config import UIConfig as CFG


class DashboardEvmRenderingMixin:
    baseline_combo: QComboBox
    evm_hint: QLabel
    evm_cost_summary: QLabel
    evm_schedule_summary: QLabel
    evm_forecast_summary: QLabel
    evm_TCPI_summary: QLabel
    evm_summary_bar: QLabel
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
        grid = QGridLayout(box)

        self.evm_hint = QLabel("Create a baseline to enable EVM metrics.")
        self.evm_hint.setWordWrap(True)

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
        for lbl in (
            self.evm_cost_summary,
            self.evm_schedule_summary,
            self.evm_forecast_summary,
            self.evm_TCPI_summary,
        ):
            lbl.setStyleSheet(
                f"font-size: 10pt; color: {CFG.COLOR_TEXT_PRIMARY};"
            )
            lbl.setWordWrap(False)
            lbl.setTextFormat(Qt.RichText)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.evm_summary_bar = QLabel("")
        self.evm_summary_bar.setTextFormat(Qt.RichText)
        self.evm_summary_bar.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.evm_summary_bar.setWordWrap(False)
        self.evm_summary_bar.setStyleSheet(
            f"font-size: 10pt; color: {CFG.COLOR_TEXT_SECONDARY};"
        )

        grid.addWidget(self.evm_hint, 0, 0, 1, 10)
        grid.addWidget(self.evm_summary_bar, 1, 0, 1, 10)

        self.cpi_lbl = QLabel("CPI")
        self.pv_lbl = QLabel("PV")
        self.spi_lbl = QLabel("SPI")
        self.ev_lbl = QLabel("EV")
        self.eac_lbl = QLabel("EAC")
        self.ac_lbl = QLabel("AC")
        self.tcpi_bac = QLabel("TCPI(BAC)")
        self.vac_lbl = QLabel("VAC")
        self.tcpi_eac = QLabel("TCPI(EAC)")

        grid.addWidget(self.cpi_lbl, 2, 0)
        grid.addWidget(self.lbl_cpi, 2, 1)
        grid.addWidget(self.pv_lbl, 2, 2)
        grid.addWidget(self.lbl_pv, 2, 3)
        grid.addWidget(self.spi_lbl, 2, 4)
        grid.addWidget(self.lbl_spi, 2, 5)
        grid.addWidget(self.ev_lbl, 2, 6)
        grid.addWidget(self.lbl_ev, 2, 7)

        grid.addWidget(self.eac_lbl, 3, 0)
        grid.addWidget(self.lbl_eac, 3, 1)
        grid.addWidget(self.ac_lbl, 3, 2)
        grid.addWidget(self.lbl_ac, 3, 3)
        grid.addWidget(self.vac_lbl, 3, 4)
        grid.addWidget(self.lbl_vac, 3, 5)
        grid.addWidget(self.tcpi_bac, 3, 6)
        grid.addWidget(self.lbl_tcpi, 3, 7)
        grid.addWidget(self.tcpi_eac, 3, 8)
        grid.addWidget(self.lbl_tcpi_eac, 3, 9)

        evm_map = getattr(CFG, "EVM_METRIC_COLORS", {})
        evm_label_map = {
            "CPI": self.lbl_cpi,
            "SPI": self.lbl_spi,
            "EAC": self.lbl_eac,
            "VAC": self.lbl_vac,
            "PV": self.lbl_pv,
            "EV": self.lbl_ev,
            "AC": self.lbl_ac,
            "TCPI": self.lbl_tcpi,
            "TCPI_EAC": self.lbl_tcpi_eac,
        }
        for key, label in evm_label_map.items():
            color = evm_map.get(key, CFG.EVM_DEFAULT_COLOR)
            label.setStyleSheet(CFG.DASHBOARD_METRIC_BOLD_TEMPLATE.format(color=color))

        for lbl in [
            self.cpi_lbl,
            self.spi_lbl,
            self.eac_lbl,
            self.vac_lbl,
            self.pv_lbl,
            self.ev_lbl,
            self.ac_lbl,
            self.tcpi_bac,
            self.tcpi_eac,
        ]:
            lbl.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)

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

    def _format_evm_part(self, text: str) -> str:
        if not text:
            return "-"
        if ":" in text:
            key, val = text.split(":", 1)
            return (
                "<span style='font-weight:600;"
                f"color:{CFG.COLOR_TEXT_SECONDARY}'>{key}:</span> "
                f"<span style='color:{CFG.COLOR_TEXT_MUTED}'>{val.strip()}</span>"
            )
        return text

    def _update_evm(self, data: DashboardData):
        if data.evm is None:
            self.evm_hint.setText("Create a baseline to enable EVM metrics.")
            if hasattr(self, "evm_cost_summary"):
                self.evm_cost_summary.setText("")
                self.evm_schedule_summary.setText("")
                self.evm_forecast_summary.setText("")
                self.evm_TCPI_summary.setText("")
            self.evm_summary_bar.setText("")
            self.lbl_cpi.setText("-")
            self.lbl_spi.setText("-")
            self.lbl_eac.setText("-")
            self.lbl_vac.setText("-")
            self.lbl_pv.setText("-")
            self.lbl_ev.setText("-")
            self.lbl_ac.setText("-")
            self.lbl_tcpi.setText("-")
            self.lbl_tcpi_eac.setText("-")
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

        parts = evm.status_text.split(". ")
        p0 = parts[0] if len(parts) > 0 else ""
        p1 = parts[1] if len(parts) > 1 else ""
        p2 = parts[2] if len(parts) > 2 else (" ".join(parts[1:]) if len(parts) > 1 else "")
        p3 = parts[3] if len(parts) > 3 else (" ".join(parts[2:]) if len(parts) > 2 else "")

        self.evm_cost_summary.setText(self._format_evm_part(p0))
        self.evm_schedule_summary.setText(self._format_evm_part(p1))
        self.evm_forecast_summary.setText(self._format_evm_part(p2))
        self.evm_TCPI_summary.setText(self._format_evm_part(p3))
        self.evm_summary_bar.setText(
            f"{self.evm_cost_summary.text()} | "
            f"{self.evm_schedule_summary.text()} | "
            f"{self.evm_forecast_summary.text()} | "
            f"{self.evm_TCPI_summary.text()}"
        )
