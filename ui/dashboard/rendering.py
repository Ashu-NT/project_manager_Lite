from __future__ import annotations

import matplotlib.dates as mdates
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QListWidgetItem,
    QTableWidgetItem,
)

from core.services.dashboard import DashboardData
from ui.styles.formatting import (
    fmt_float,
    fmt_int,
    fmt_money,
    fmt_percent,
    fmt_ratio,
)
from ui.styles.ui_config import UIConfig as CFG


class DashboardRenderingMixin:
    def _clear_dashboard(self):
        self.alerts_list.clear()
        self.upcoming_table.setRowCount(0)

        self.burndown_chart.ax.clear()
        self.resource_chart.ax.clear()
        self.burndown_chart.redraw()
        self.resource_chart.redraw()

        try:
            self.kpi_tasks.findChildren(QLabel)[1].setText("0 / 0")
            self.kpi_tasks.findChildren(QLabel)[2].setText("Completed / Total")
            self.kpi_critical.findChildren(QLabel)[1].setText("0")
            self.kpi_late.findChildren(QLabel)[1].setText("0")
            self.kpi_cost.findChildren(QLabel)[1].setText("0.00")
            self.kpi_cost.findChildren(QLabel)[2].setText("Actual - Planned")
            self.kpi_progress.findChildren(QLabel)[1].setText("0%")
        except Exception:
            pass

        if hasattr(self, "project_title_lbl"):
            self.project_title_lbl.setText("")
            self.project_meta_start.setText("")
            self.project_meta_end.setText("")
            self.project_meta_duration.setText("")

        if hasattr(self, "evm_hint"):
            self.evm_hint.setText("Create a baseline to enable EVM metrics.")
            if hasattr(self, "evm_cost_summary"):
                self.evm_cost_summary.setText("")
                self.evm_schedule_summary.setText("")
                self.evm_forecast_summary.setText("")
                self.evm_TCPI_summary.setText("")
            self.lbl_cpi.setText("-")
            self.lbl_spi.setText("-")
            self.lbl_eac.setText("-")
            self.lbl_vac.setText("-")
            self.lbl_pv.setText("-")
            self.lbl_ev.setText("-")
            self.lbl_ac.setText("-")

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
            lbl.setStyleSheet("font-size: 10pt; color: #333333;")
            lbl.setWordWrap(False)
            lbl.setTextFormat(Qt.RichText)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.evm_summary_bar = QLabel("")
        self.evm_summary_bar.setTextFormat(Qt.RichText)
        self.evm_summary_bar.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.evm_summary_bar.setWordWrap(False)
        self.evm_summary_bar.setStyleSheet("font-size: 10pt; color: #444444;")

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
            """
            QGroupBox {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                margin-top: 8px;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #444444;
                font-weight: bold;
            }
        """
        )

        return box

    def _format_evm_part(self, text: str) -> str:
        if not text:
            return "-"
        if ":" in text:
            key, val = text.split(":", 1)
            return f"<span style='font-weight:600;color:#444'>{key}:</span> <span style='color:#666'>{val.strip()}</span>"
        return text

    def _update_summary(self, project_name: str, data: DashboardData):
        k = data.kpi
        start = k.start_date.isoformat() if k.start_date else "-"
        end = k.end_date.isoformat() if k.end_date else "-"
        title = project_name or (getattr(k, "name", None) or "")
        self.project_title_lbl.setText(title)
        self.project_title_lbl.setVisible(True)
        self.project_title_lbl.setWordWrap(False)

        self.project_meta_start.setText(f"{CFG.DASHBOARD_META_START_PREFIX} {start}")
        self.project_meta_start.setVisible(True)
        self.project_meta_end.setText(f"{CFG.DASHBOARD_META_END_PREFIX} {end}")
        self.project_meta_end.setVisible(True)
        self.project_meta_duration.setText(
            f"{CFG.DASHBOARD_META_DURATION_PREFIX} {k.duration_working_days} working days"
        )
        self.project_meta_duration.setVisible(True)

    def _update_kpis(self, data: DashboardData):
        k = data.kpi
        tasks_value = self.kpi_tasks.findChildren(QLabel)[1]
        tasks_sub = self.kpi_tasks.findChildren(QLabel)[2]
        tasks_value.setText(f"{fmt_int(k.tasks_completed)} / {fmt_int(k.tasks_total)}")
        tasks_sub.setText("Completed / Total")

        crit_value = self.kpi_critical.findChildren(QLabel)[1]
        crit_value.setText(fmt_int(k.critical_tasks))

        late_value = self.kpi_late.findChildren(QLabel)[1]
        late_value.setText(fmt_int(k.late_tasks))

        cost_value = self.kpi_cost.findChildren(QLabel)[1]
        cost_sub = self.kpi_cost.findChildren(QLabel)[2]
        cost_value.setText(f"{fmt_float(k.cost_variance,2)}")
        cost_sub.setText("Actual - Planned")

        pct = 0.0
        if k.tasks_total > 0:
            pct = 100.0 * k.tasks_completed / k.tasks_total
        prog_value = self.kpi_progress.findChildren(QLabel)[1]
        prog_value.setText(f"{fmt_percent(pct,2)}")

    def _update_burndown_chart(self, data: DashboardData):
        self.burndown_chart.ax.clear()
        pts = data.burndown
        if not pts:
            self.burndown_chart.ax.set_title("No burndown data")
            self.burndown_chart.redraw()
            return

        dates = [p.day for p in pts]
        rem = [p.remaining_tasks for p in pts]

        self.burndown_chart.ax.plot(dates, rem, marker="o")

        self.burndown_chart.ax.set_title("Burndown (remaining tasks)")
        self.burndown_chart.ax.set_xlabel("Date", fontsize=10)
        self.burndown_chart.ax.set_ylabel("Remaining tasks", fontsize=10)
        self.burndown_chart.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.burndown_chart.ax.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(mdates.AutoDateLocator())
        )
        self.burndown_chart.fig.autofmt_xdate(rotation=30)
        self.burndown_chart.ax.grid(True, linestyle=":", linewidth=0.5)

        self.burndown_chart.fig.tight_layout()
        self.burndown_chart.redraw()

    def _update_resource_chart(self, data: DashboardData):
        self.resource_chart.ax.clear()
        rows = data.resource_load
        if not rows:
            self.resource_chart.ax.set_title("No resource load data")
            self.resource_chart.redraw()
            return

        names = [r.resource_name for r in rows]
        allocs = [r.total_allocation_percent for r in rows]

        x = range(len(names))
        bars = self.resource_chart.ax.bar(x, allocs)
        for i, r in enumerate(rows):
            if r.total_allocation_percent > 100.0:
                bars[i].set_color("#d0021b")

        self.resource_chart.ax.set_xticks(list(x))
        self.resource_chart.ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
        self.resource_chart.ax.set_ylabel("Allocation %", fontsize=10)
        self.resource_chart.ax.set_title("Resource load")
        self.resource_chart.ax.axhline(100.0, color="red", linestyle="--", linewidth=0.5)
        self.resource_chart.ax.grid(True, axis="y", linestyle=":", linewidth=0.5)

        self.resource_chart.fig.tight_layout()
        self.resource_chart.redraw()

    def _update_alerts(self, data: DashboardData):
        self.alerts_list.clear()
        if not data.alerts:
            self.alerts_list.addItem("No alerts. Everything looks good.")
            return

        for msg in data.alerts:
            item = QListWidgetItem("WARNING: " + msg)
            item.setForeground(QColor("#d0021b"))
            self.alerts_list.addItem(item)

    def _update_upcoming(self, data: DashboardData):
        self.upcoming_table.setRowCount(0)
        ups = data.upcoming_tasks
        if not ups:
            return

        self.upcoming_table.setRowCount(len(ups))
        for row, u in enumerate(ups):
            def set_cell(col, text, color_bg=None):
                item = QTableWidgetItem(text)
                if color_bg:
                    item.setBackground(color_bg)
                self.upcoming_table.setItem(row, col, item)

            set_cell(0, u.name)
            set_cell(1, u.start_date.isoformat() if u.start_date else "-")
            set_cell(2, u.end_date.isoformat() if u.end_date else "-")
            set_cell(3, f"{u.percent_complete:.0f}%")
            set_cell(4, u.main_resource or "-")

            if u.is_late:
                for col in range(5):
                    it = self.upcoming_table.item(row, col)
                    it.setBackground(QColor("#ffe5e5"))

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
