from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError


class TaskValidationMixin:
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository | None
    _project_repo: ProjectRepository | None
    _overallocation_policy: str
    _last_overallocation_warning: str | None

    def _validate_task_within_project_dates(
        self, project_id: str, task_start: date | None, task_end: date | None
    ):
        if self._project_repo is None:
            return
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        project_start = getattr(project, "start_date", None)
        project_end = getattr(project, "end_date", None)

        if project_start and task_start and task_start < project_start:
            raise ValidationError(
                f"Task start date ({task_start}) can not be before project start ({project_start})",
                code="TASK_INVALID_DATE",
            )
        if project_end and task_start and task_start > project_end:
            raise ValidationError(
                f"Task start date ({task_start}) can not be after project end ({project_end})",
                code="TASK_INVALID_DATE",
            )
        if project_start and task_end and task_end < project_start:
            raise ValidationError(
                f"Task end date ({task_end}) can not be before project start ({project_start})",
                code="TASK_INVALID_DATE",
            )
        if project_end and task_end and task_end > project_end:
            raise ValidationError(
                f"Task end date ({task_end}) can not be after project end ({project_end})",
                code="TASK_INVALID_DATE",
            )

    def _iter_workdays(self, start: date, end: date):
        if not start or not end:
            return
        if end < start:
            start, end = end, start
        current = start
        while current <= end:
            if current.weekday() < 5:
                yield current
            current += timedelta(days=1)

    def _check_resource_overallocation(
        self,
        project_id: str,
        resource_id: str,
        new_task_id: str,
        new_alloc_percent: float,
        exclude_assignment_id: str | None = None,
    ) -> str | None:
        self._last_overallocation_warning = None
        new_task = self._task_repo.get(new_task_id)
        if not new_task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        new_start = getattr(new_task, "start_date", None)
        new_end = getattr(new_task, "end_date", None)
        if not new_start or not new_end:
            return None

        capacity_percent = 100.0
        resource_repo = getattr(self, "_resource_repo", None)
        if resource_repo is not None:
            resource = resource_repo.get(resource_id)
            raw_capacity = float(getattr(resource, "capacity_percent", 100.0) or 100.0) if resource else 100.0
            if raw_capacity > 0.0:
                capacity_percent = raw_capacity

        assignments = self._assignment_repo.list_by_resource(resource_id)
        if not assignments:
            return None

        daily_total: dict[date, float] = {}
        daily_tasks: dict[date, list[str]] = {}

        for assignment in assignments:
            if exclude_assignment_id and getattr(assignment, "id", None) == exclude_assignment_id:
                continue
            task = self._task_repo.get(assignment.task_id)
            if not task or getattr(task, "project_id", None) != project_id:
                continue

            task_start = getattr(task, "start_date", None)
            task_end = getattr(task, "end_date", None)
            if not task_start or not task_end:
                continue

            overlap_start = max(new_start, task_start)
            overlap_end = min(new_end, task_end)
            if overlap_end < overlap_start:
                continue

            allocation = float(getattr(assignment, "allocation_percent", 0.0) or 0.0)
            if allocation <= 0:
                continue

            for workday in self._iter_workdays(overlap_start, overlap_end):
                daily_total[workday] = daily_total.get(workday, 0.0) + allocation
                daily_tasks.setdefault(workday, []).append(getattr(task, "name", assignment.task_id))

        for workday in self._iter_workdays(new_start, new_end):
            daily_total[workday] = daily_total.get(workday, 0.0) + float(new_alloc_percent or 0.0)
            daily_tasks.setdefault(workday, []).append(getattr(new_task, "name", new_task_id))

        for workday in sorted(daily_total.keys()):
            total = daily_total[workday]
            if total > capacity_percent + 1e-9:
                tasks = daily_tasks.get(workday, [])[:6]
                extra = "..." if len(daily_tasks.get(workday, [])) > 6 else ""
                message = (
                    f"Resource would be over-allocated on {workday.isoformat()} "
                    f"({total:.1f}% > {capacity_percent:.1f}%).\n"
                    f"Tasks: {', '.join(tasks)}{extra}"
                )
                if getattr(self, "_overallocation_policy", "warn") == "strict":
                    raise BusinessRuleError(message, code="RESOURCE_OVERALLOCATED")
                self._last_overallocation_warning = message
                return message
        return None


__all__ = ["TaskValidationMixin"]
