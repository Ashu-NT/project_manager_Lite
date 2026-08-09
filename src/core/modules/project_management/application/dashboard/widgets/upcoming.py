from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.application.dashboard.models.dashboard_models import UpcomingTask
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks


class DashboardUpcomingMixin:
    _tasks: TaskService
    _resources: ResourceService

    def _build_upcoming_tasks(
        self,
        project_id: str,
        *,
        tasks: list[object] | None = None,
        assignments_by_task: dict[str, list[object]] | None = None,
        resources_by_id: dict[str, object] | None = None,
    ) -> list[UpcomingTask]:
        today = date.today()
        horizon = today + timedelta(days=14)

        tasks = (
            tasks
            if tasks is not None
            else select_leaf_tasks(self._tasks.list_tasks_for_project(project_id))
        )
        if resources_by_id is None:
            resources_by_id = {
                resource.id: resource for resource in self._resources.list_resources()
            }
        upcoming: list[UpcomingTask] = []

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

            assignments = (
                assignments_by_task.get(task.id, [])
                if assignments_by_task is not None
                else self._tasks.list_assignments_for_task(task.id)
            )
            main_resource = None
            if assignments:
                assignment = max(assignments, key=lambda item: item.allocation_percent or 0.0)
                main_resource = getattr(assignment, "resource_name", None)
                if not main_resource:
                    resource = resources_by_id.get(getattr(assignment, "resource_id", ""))
                    main_resource = getattr(resource, "name", None)

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
