from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta

from src.core.modules.project_management.application.dashboard.models.dashboard_models import (
    UpcomingTask,
)
from src.core.modules.project_management.application.resources.dto.responses.catalog import (
    ResourceResponse,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment


class DashboardUpcomingWidget:
    """Next-14-day task list built from already-loaded tasks/assignments."""

    def build(
        self,
        *,
        tasks: list[Task],
        assignments_by_task: Mapping[str, list[TaskAssignment]],
        resources_by_id: Mapping[str, ResourceResponse],
    ) -> list[UpcomingTask]:
        today = date.today()  # noqa: DTZ011
        horizon = today + timedelta(days=14)

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

            assignments = assignments_by_task.get(task.id, [])
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


__all__ = ["DashboardUpcomingWidget"]
