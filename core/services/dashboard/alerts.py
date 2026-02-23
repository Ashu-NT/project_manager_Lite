from __future__ import annotations

from datetime import date
from typing import List

from core.services.task.service import TaskService
from core.services.reporting.models import ProjectKPI, ResourceLoadRow


class DashboardAlertsMixin:
    _tasks: TaskService

    def _build_alerts(
        self,
        project_id: str,
        kpi: ProjectKPI,
        resource_load: List[ResourceLoadRow],
    ) -> List[str]:
        alerts: List[str] = []
        today = date.today()

        for row in resource_load:
            if row.total_allocation_percent > 100.0:
                alerts.append(
                    f'Resource "{row.resource_name}" is overloaded '
                    f"({row.total_allocation_percent:.1f}% allocation on {row.tasks_count} tasks)."
                )

        if kpi.late_tasks > 0:
            alerts.append(f"There are {kpi.late_tasks} late tasks in this project.")

        tasks = self._tasks.list_tasks_for_project(project_id)
        missing_dates = [
            task
            for task in tasks
            if (task.duration_days or 0) > 0
            and (task.start_date is None or task.end_date is None)
        ]
        if missing_dates:
            alerts.append(
                f"{len(missing_dates)} task(s) have duration but are missing start or end dates."
            )

        if not tasks:
            alerts.append("This project has no tasks yet.")
        elif not (kpi.start_date and kpi.end_date):
            alerts.append("Project schedule has incomplete dates. Check task start/end.")

        if kpi.end_date and kpi.end_date < today and kpi.tasks_completed < kpi.tasks_total:
            alerts.append(f"Project appears delayed: planned finish was {kpi.end_date.isoformat()}.")

        for task in tasks:
            if task.deadline and task.end_date and task.end_date > task.deadline:
                alerts.append(f"Task '{task.name}' missed its deadline.")

            priority = int(getattr(task, "priority", 0) or 0)
            if priority >= 80 and task.deadline and task.end_date and task.end_date > task.deadline:
                alerts.append(f"High-priority task '{task.name}' is late.")

        return alerts
