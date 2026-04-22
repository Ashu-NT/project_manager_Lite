from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProjectDashboardMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class ProjectDashboardOverviewDescriptor:
    title: str
    subtitle: str
    metrics: tuple[ProjectDashboardMetricDescriptor, ...]


def _fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _fmt_float(value: Any, decimals: int = 2) -> str:
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return f"{0.0:,.{decimals}f}"


def _fmt_percent(value: Any, decimals: int = 2) -> str:
    return f"{_fmt_float(value, decimals)}%"


class ProjectManagementDashboardDesktopApi:
    def build_empty_overview(self) -> ProjectDashboardOverviewDescriptor:
        return ProjectDashboardOverviewDescriptor(
            title="Dashboard",
            subtitle="Select a project to see schedule and cost health.",
            metrics=(
                ProjectDashboardMetricDescriptor("Tasks", "0 / 0", "Done / Total"),
                ProjectDashboardMetricDescriptor("Progress", "0.00%", "Completion"),
                ProjectDashboardMetricDescriptor("In flight", "0", "Active work"),
                ProjectDashboardMetricDescriptor("Blocked", "0", "Needs action"),
                ProjectDashboardMetricDescriptor("Critical", "0", "Path pressure"),
                ProjectDashboardMetricDescriptor("Late", "0", "Behind plan"),
                ProjectDashboardMetricDescriptor("Cost variance", "0.00", "Actual - Planned"),
                ProjectDashboardMetricDescriptor("Spend vs plan", "0 / 0", "Actual / planned"),
            ),
        )

    def build_overview_from_dashboard_data(
        self, *, project_name: str, dashboard_data: Any
    ) -> ProjectDashboardOverviewDescriptor:
        kpi = dashboard_data.kpi
        tasks_total = int(getattr(kpi, "tasks_total", 0) or 0)
        tasks_completed = int(getattr(kpi, "tasks_completed", 0) or 0)
        progress = 100.0 * tasks_completed / tasks_total if tasks_total else 0.0
        title = project_name or getattr(kpi, "name", "") or "Dashboard"

        return ProjectDashboardOverviewDescriptor(
            title=title,
            subtitle="Project execution health",
            metrics=(
                ProjectDashboardMetricDescriptor(
                    "Tasks",
                    f"{_fmt_int(tasks_completed)} / {_fmt_int(tasks_total)}",
                    "Done / Total",
                ),
                ProjectDashboardMetricDescriptor("Progress", _fmt_percent(progress), "Completion"),
                ProjectDashboardMetricDescriptor(
                    "In flight",
                    _fmt_int(getattr(kpi, "tasks_in_progress", 0)),
                    "Active work",
                ),
                ProjectDashboardMetricDescriptor(
                    "Blocked",
                    _fmt_int(getattr(kpi, "task_blocked", 0)),
                    "Needs action",
                ),
                ProjectDashboardMetricDescriptor(
                    "Critical",
                    _fmt_int(getattr(kpi, "critical_tasks", 0)),
                    "Path pressure",
                ),
                ProjectDashboardMetricDescriptor(
                    "Late",
                    _fmt_int(getattr(kpi, "late_tasks", 0)),
                    "Behind plan",
                ),
                ProjectDashboardMetricDescriptor(
                    "Cost variance",
                    _fmt_float(getattr(kpi, "cost_variance", 0.0)),
                    "Actual - Planned",
                ),
                ProjectDashboardMetricDescriptor(
                    "Spend vs plan",
                    (
                        f"{_fmt_float(getattr(kpi, 'total_actual_cost', 0.0), 0)} / "
                        f"{_fmt_float(getattr(kpi, 'total_planned_cost', 0.0), 0)}"
                    ),
                    "Actual / planned",
                ),
            ),
        )


def build_project_management_dashboard_desktop_api() -> ProjectManagementDashboardDesktopApi:
    return ProjectManagementDashboardDesktopApi()


__all__ = [
    "ProjectDashboardMetricDescriptor",
    "ProjectDashboardOverviewDescriptor",
    "ProjectManagementDashboardDesktopApi",
    "build_project_management_dashboard_desktop_api",
]
