from __future__ import annotations

from PySide6.QtWidgets import QLabel

from core.services.dashboard import DashboardData
from ui.styles.formatting import fmt_float, fmt_int, fmt_percent
from ui.styles.ui_config import UIConfig as CFG


class DashboardSummaryRenderingMixin:
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
