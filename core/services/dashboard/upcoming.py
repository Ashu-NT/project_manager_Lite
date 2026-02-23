from __future__ import annotations

from datetime import date, timedelta
from typing import List

from core.services.dashboard.models import UpcomingTask
from core.services.task.service import TaskService


class DashboardUpcomingMixin:
    _tasks: TaskService

    def _build_upcoming_tasks(self, project_id: str) -> List[UpcomingTask]:
        today = date.today()
        horizon = today + timedelta(days=14)

        tasks = self._tasks.list_tasks_for_project(project_id)
        upcoming: List[UpcomingTask] = []

        for task in tasks:
            if task.start_date is None:
                continue
            if task.start_date < today:
                continue
            if task.start_date > horizon:
                continue
            if str(task.status) in ("TaskStatus.DONE", "DONE"):
                continue
            if str(task.status) in ("TaskStatus.BLOCKED", "BLOCKED"):
                continue

            assignments = self._tasks.list_assignments_for_task(task.id)
            main_resource = None
            if assignments:
                assignment = max(assignments, key=lambda item: item.allocation_percent or 0.0)
                main_resource = getattr(assignment, "resource_name", None)

            percent_complete = task.percent_complete or 0.0
            is_late = (
                task.end_date is not None
                and task.end_date < today
                and percent_complete < 100.0
            )

            upcoming.append(
                UpcomingTask(
                    task_id=task.id,
                    name=task.name,
                    start_date=task.start_date,
                    end_date=task.end_date,
                    percent_complete=percent_complete,
                    main_resource=main_resource,
                    is_late=is_late,
                    is_critical=False,
                )
            )

        upcoming.sort(key=lambda row: (row.start_date or date.max))
        return upcoming
