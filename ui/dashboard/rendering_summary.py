from __future__ import annotations

from PySide6.QtWidgets import QLabel
from core.services.dashboard import DashboardData
from ui.dashboard.widgets import ChartWidget, KpiCard
from ui.styles.formatting import fmt_float, fmt_int, fmt_percent
from ui.styles.ui_config import UIConfig as CFG

class DashboardSummaryRenderingMixin:
    conflicts_table: object
    btn_auto_level: object; btn_manual_shift: object; btn_open_conflicts: object
    btn_open_alerts: object; btn_open_upcoming: object
    burndown_chart: ChartWidget; resource_chart: ChartWidget
    kpi_tasks: KpiCard; kpi_progress: KpiCard; kpi_inflight: KpiCard; kpi_blocked: KpiCard
    kpi_critical: KpiCard; kpi_late: KpiCard; kpi_cost: KpiCard; kpi_budget: KpiCard
    project_title_lbl: QLabel; project_subtitle_lbl: QLabel; project_mode_badge: QLabel
    project_meta_scope: QLabel; project_meta_start: QLabel; project_meta_end: QLabel; project_meta_duration: QLabel
    dashboard_mode_badge: QLabel; dashboard_scope_hint: QLabel

    @staticmethod
    def _set_card(card: KpiCard, title: str, value: str, subtitle: str = "") -> None:
        card.set_title(title); card.set_value(value); card.set_subtitle(subtitle)

    @staticmethod
    def _set_optional_label(label: QLabel, text: str) -> None:
        label.setText(text)
        label.setVisible(bool(text))

    def _clear_dashboard(self):
        self.conflicts_table.setRowCount(0)
        if hasattr(self, "btn_auto_level"): self.btn_auto_level.setEnabled(False)
        if hasattr(self, "btn_manual_shift"): self.btn_manual_shift.setEnabled(False)
        self._current_alert_rows = []
        self._current_alert_summary = "0 active alerts"
        self._current_upcoming_rows = []
        if hasattr(self, "btn_open_conflicts"): self.btn_open_conflicts.set_badge(0, "success")
        if hasattr(self, "btn_open_alerts"): self.btn_open_alerts.set_badge(0, "success")
        if hasattr(self, "btn_open_upcoming"): self.btn_open_upcoming.set_badge(0, "neutral")
        if getattr(self, "_alerts_dialog", None) is not None: self._alerts_dialog.set_alert_rows([], self._current_alert_summary)
        if getattr(self, "_upcoming_dialog", None) is not None: self._upcoming_dialog.set_upcoming_rows([])
        self.burndown_chart.ax.clear()
        self.resource_chart.ax.clear()
        self.burndown_chart.redraw()
        self.resource_chart.redraw()
        self._set_card(self.kpi_tasks, "Tasks", "0 / 0", "Done / Total")
        self._set_card(self.kpi_progress, "Progress", "0%", "Completion")
        self._set_card(self.kpi_inflight, "In flight", "0", "Active work")
        self._set_card(self.kpi_blocked, "Blocked", "0", "Needs action")
        self._set_card(self.kpi_critical, "Critical", "0", "Path pressure")
        self._set_card(self.kpi_late, "Late", "0", "Behind plan")
        self._set_card(self.kpi_cost, "Cost variance", "0.00", "Actual - planned")
        self._set_card(self.kpi_budget, "Spend vs plan", "0 / 0", "Actual / planned")
        if hasattr(self, "kpi_group"): self.kpi_group.setTitle("Key Metrics")
        if hasattr(self, "project_title_lbl"):
            self.project_title_lbl.setText("Select a project to see schedule and cost health.")
            self._set_optional_label(self.project_subtitle_lbl, "")
            self.project_mode_badge.setText("Project View")
            self._set_optional_label(self.project_meta_scope, "")
            self._set_optional_label(self.project_meta_start, "")
            self._set_optional_label(self.project_meta_end, "")
            self._set_optional_label(self.project_meta_duration, "")
        if hasattr(self, "dashboard_mode_badge"):
            self.dashboard_mode_badge.setText("Live Panels"); self.dashboard_scope_hint.setText("4 panels active")
        if hasattr(self, "_reset_evm_view"): self._reset_evm_view()
        if hasattr(self, "_clear_portfolio_panel"): self._clear_portfolio_panel()
        if hasattr(self, "_clear_professional_panels"): self._clear_professional_panels()
        if hasattr(self, "_sync_dashboard_panel_visibility"): self._sync_dashboard_panel_visibility()

    def _update_summary(self, project_name: str, data: DashboardData):
        k = data.kpi
        portfolio = getattr(data, "portfolio", None)
        start = k.start_date.isoformat() if k.start_date else "-"
        end = k.end_date.isoformat() if k.end_date else "-"
        title = project_name or (getattr(k, "name", None) or "")
        if portfolio is not None:
            title = "Portfolio Overview"; subtitle, mode_text, scope_text = "", "Portfolio View", "Scope Cross-project control"
        else:
            subtitle, mode_text, scope_text = "", "Project View", "Scope Project execution"
        self.project_title_lbl.setText(title)
        self._set_optional_label(self.project_subtitle_lbl, subtitle)
        self.project_mode_badge.setText(mode_text)
        self._set_optional_label(self.project_meta_scope, scope_text)
        self._set_optional_label(self.project_meta_start, f"{CFG.DASHBOARD_META_START_PREFIX} {start}")
        self._set_optional_label(self.project_meta_end, f"{CFG.DASHBOARD_META_END_PREFIX} {end}")
        self._set_optional_label(
            self.project_meta_duration,
            f"{CFG.DASHBOARD_META_DURATION_PREFIX} {k.duration_working_days} working days"
            if portfolio is None
            else f"Projects {portfolio.projects_total} | Active {portfolio.active_projects} | At risk {portfolio.at_risk_projects}"
        )
        if hasattr(self, "_sync_dashboard_panel_visibility"): self._sync_dashboard_panel_visibility()
        if hasattr(self, "dashboard_mode_badge"):
            active_count = self._active_dashboard_panel_count() if hasattr(self, "_active_dashboard_panel_count") else 0
            self.dashboard_mode_badge.setText("Live Panels"); self.dashboard_scope_hint.setText(f"{active_count} panels active")

    def _update_kpis(self, data: DashboardData):
        k = data.kpi
        portfolio = getattr(data, "portfolio", None)
        overloaded_count = sum(
            1
            for row in getattr(data, "resource_load", []) or []
            if float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0) > 100.0
        )
        if portfolio is None:
            self.kpi_group.setTitle("Key Metrics")
            self._set_card(self.kpi_tasks, "Tasks", f"{fmt_int(k.tasks_completed)} / {fmt_int(k.tasks_total)}", "Done / Total")
            self._set_card(self.kpi_inflight, "In flight", fmt_int(k.tasks_in_progress), "Active work")
            self._set_card(self.kpi_blocked, "Blocked", fmt_int(k.task_blocked), "Needs action")
            self._set_card(self.kpi_budget, "Spend vs plan", f"{fmt_float(k.total_actual_cost,0)} / {fmt_float(k.total_planned_cost,0)}", "Actual / planned")
            critical_value = fmt_int(k.critical_tasks)
        else:
            self.kpi_group.setTitle("Portfolio Metrics")
            self._set_card(self.kpi_tasks, "Projects", f"{fmt_int(portfolio.completed_projects)} / {fmt_int(portfolio.projects_total)}", "Done / Total")
            self._set_card(self.kpi_inflight, "Active", fmt_int(portfolio.active_projects), "Active projects")
            self._set_card(self.kpi_blocked, "On hold", fmt_int(portfolio.on_hold_projects), "Paused projects")
            self._set_card(self.kpi_budget, "Overloaded", fmt_int(overloaded_count), "Resources > 100%")
            critical_value = fmt_int(portfolio.at_risk_projects)
        self.kpi_progress.set_title("Progress" if portfolio is None else "Task progress")
        self.kpi_critical.set_title("Critical" if portfolio is None else "At risk")
        self.kpi_late.set_title("Late" if portfolio is None else "Late tasks")
        self.kpi_cost.set_title("Cost variance" if portfolio is None else "Portfolio variance")
        self.kpi_critical.set_value(critical_value)
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
        self.kpi_progress.set_subtitle("Completion")
