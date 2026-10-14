from __future__ import annotations

from datetime import timedelta

from src.core.modules.project_management.application.dashboard.models.dashboard_models import (
    BurndownPoint,
)
from src.core.modules.project_management.application.dashboard.models.report_models import (
    ProjectKPI,
)
from src.core.modules.project_management.domain.tasks.task import Task


class DashboardBurndownBuilder:
    def build(
        self,
        *,
        kpi: ProjectKPI,
        tasks: list[Task],
    ) -> list[BurndownPoint]:
        """
        Simple logical burndown: count of remaining (not completed) tasks per day between
        project start and end. For visualization in the dashboard.
        """
        if not tasks or not (kpi.start_date and kpi.end_date):
            return []

        start = kpi.start_date
        end = kpi.end_date
        if start > end:
            start, end = end, start

        points: list[BurndownPoint] = []
        current = start
        while current <= end:
            remaining = 0
            for task in tasks:
                pct = task.percent_complete or 0.0
                if pct < 100.0:
                    if task.start_date and task.end_date:
                        if task.start_date <= current <= task.end_date:
                            remaining += 1
                    else:
                        remaining += 1

            points.append(BurndownPoint(day=current, remaining_tasks=remaining))
            current = current + timedelta(days=1)

        return points


__all__ = ["DashboardBurndownBuilder"]
