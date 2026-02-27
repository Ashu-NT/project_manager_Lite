from __future__ import annotations

from PySide6.QtWidgets import QLabel

from core.services.dashboard import DashboardData
from ui.dashboard.widgets import ChartWidget, KpiCard
from ui.styles.formatting import fmt_float, fmt_int, fmt_percent
from ui.styles.ui_config import UIConfig as CFG


class DashboardSummaryRenderingMixin:
    conflicts_table: object
    btn_auto_level: object
    btn_manual_shift: object
    btn_open_conflicts: object
    btn_open_alerts: object
    btn_open_upcoming: object
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
        self.conflicts_table.setRowCount(0)
        if hasattr(self, "btn_auto_level"):
            self.btn_auto_level.setEnabled(False)
        if hasattr(self, "btn_manual_shift"):
            self.btn_manual_shift.setEnabled(False)
        self._current_alert_rows = []
        self._current_alert_summary = "0 active alerts"
        self._current_upcoming_rows = []
        if hasattr(self, "btn_open_conflicts"):
            self.btn_open_conflicts.set_badge(0, "success")
        if hasattr(self, "btn_open_alerts"):
            self.btn_open_alerts.set_badge(0, "success")
        if hasattr(self, "btn_open_upcoming"):
            self.btn_open_upcoming.set_badge(0, "neutral")
        if getattr(self, "_alerts_dialog", None) is not None:
            self._alerts_dialog.set_alert_rows([], self._current_alert_summary)
        if getattr(self, "_upcoming_dialog", None) is not None:
            self._upcoming_dialog.set_upcoming_rows([])

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

        if hasattr(self, "_reset_evm_view"):
            self._reset_evm_view()

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
        cost_subtitle = "Actual - Planned"
        sources = getattr(data, "cost_sources", None)
        if sources and getattr(sources, "rows", None):
            actual_map = {row.source_key: float(row.actual or 0.0) for row in sources.rows}
            cost_subtitle = (
                f"Direct Cost {fmt_float(actual_map.get('DIRECT_COST', 0.0), 0)} | "
                f"Computed Labor {fmt_float(actual_map.get('COMPUTED_LABOR', 0.0), 0)} | "
                f"Labor Adjustment {fmt_float(actual_map.get('LABOR_ADJUSTMENT', 0.0), 0)}"
            )
        self.kpi_cost.set_subtitle(cost_subtitle)

        pct = 0.0
        if k.tasks_total > 0:
            pct = 100.0 * k.tasks_completed / k.tasks_total
        self.kpi_progress.set_value(f"{fmt_percent(pct,2)}")
