from __future__ import annotations

from PySide6.QtWidgets import QLabel, QListWidget, QTableWidget

from core.services.dashboard import DashboardData
from ui.dashboard.widgets import ChartWidget, KpiCard
from ui.styles.formatting import fmt_float, fmt_int, fmt_percent
from ui.styles.ui_config import UIConfig as CFG


class DashboardSummaryRenderingMixin:
    alerts_list: QListWidget
    upcoming_table: QTableWidget
    burndown_chart: ChartWidget
    resource_chart: ChartWidget
    kpi_tasks: KpiCard
    kpi_critical: KpiCard
    kpi_late: KpiCard
    kpi_cost: KpiCard
    kpi_progress: KpiCard
    project_title_lbl: QLabel
    project_meta_start: QLabel
    project_meta_end: QLabel
    project_meta_duration: QLabel

    def _clear_dashboard(self):
        self.alerts_list.clear()
        self.upcoming_table.setRowCount(0)

        self.burndown_chart.ax.clear()
        self.resource_chart.ax.clear()
        self.burndown_chart.redraw()
        self.resource_chart.redraw()

        self.kpi_tasks.set_value("0 / 0")
        self.kpi_tasks.set_subtitle("Completed / Total")
        self.kpi_critical.set_value("0")
        self.kpi_late.set_value("0")
        self.kpi_cost.set_value("0.00")
        self.kpi_cost.set_subtitle("Actual - Planned")
        self.kpi_progress.set_value("0%")

        if hasattr(self, "project_title_lbl"):
            self.project_title_lbl.setText("Select a project to see schedule and cost health.")
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
        self.kpi_tasks.set_value(f"{fmt_int(k.tasks_completed)} / {fmt_int(k.tasks_total)}")
        self.kpi_tasks.set_subtitle("Completed / Total")

        self.kpi_critical.set_value(fmt_int(k.critical_tasks))

        self.kpi_late.set_value(fmt_int(k.late_tasks))

        self.kpi_cost.set_value(f"{fmt_float(k.cost_variance,2)}")
        self.kpi_cost.set_subtitle("Actual - Planned")

        pct = 0.0
        if k.tasks_total > 0:
            pct = 100.0 * k.tasks_completed / k.tasks_total
        self.kpi_progress.set_value(f"{fmt_percent(pct,2)}")
