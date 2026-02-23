from __future__ import annotations

from datetime import timedelta
from typing import List

from core.services.dashboard.models import BurndownPoint
from core.services.reporting.service import ReportingService
from core.services.task.service import TaskService


class DashboardBurndownMixin:
    _reporting: ReportingService
    _tasks: TaskService

    def _build_burndown(self, project_id: str) -> List[BurndownPoint]:
        """
        Simple logical burndown: count of remaining (not completed) tasks per day between
        project start and end. For visualization in the dashboard.
        """
        kpi = self._reporting.get_project_kpis(project_id)
        tasks = self._tasks.list_tasks_for_project(project_id)

        if not tasks or not (kpi.start_date and kpi.end_date):
            return []

        start = kpi.start_date
        end = kpi.end_date
        if start > end:
            start, end = end, start

        points: List[BurndownPoint] = []
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
