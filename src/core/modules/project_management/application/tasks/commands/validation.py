from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError


class TaskValidationMixin:
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository | None
    _project_repo: ProjectRepository | None
    _overallocation_policy: str
    _last_overallocation_warning: str | None

    def _validate_dates(self, start_date, end_date, duration_days):
        if start_date and end_date and end_date < start_date:
            raise ValidationError("Task deadline cannot be before start_date.")

        if duration_days is not None and duration_days < 0:
            raise ValidationError("Task duration_days cannot be negative.")

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

    def _validate_not_self_dependency(self, predecessor_id: str, successor_id: str):
        if predecessor_id == successor_id:
            raise ValidationError("A task cannot depend on itself.")

    def _validate_task_name(self, name: str) -> None:
        if not name.strip():
            raise ValidationError("Task name cannot be empty.", code="TASK_NAME_EMPTY")
        if len(name.strip()) < 3:
            raise ValidationError(
                "Task name must be at least 3 characters.", code="TASK_NAME_TOO_SHORT"
            )
        if any(char in name for char in ["/", "\\", "?", "%", "*", ":", "|", '"', "<", ">"]):
            raise ValidationError(
                "Task name contains invalid characters.", code="TASK_NAME_INVALID_CHARS"
            )

    def _check_no_circular_dependency(
        self, project_id: str, predecessor_id: str, successor_id: str
    ) -> None:
        dependencies = self._dependency_repo.list_by_project(project_id)
        project_task_ids = {task.id for task in self._task_repo.list_by_project(project_id)}
        dependencies = [
            dependency
            for dependency in dependencies
            if dependency.predecessor_task_id in project_task_ids
            and dependency.successor_task_id in project_task_ids
        ]

        graph: dict[str, list[str]] = {}
        for dependency in dependencies:
            graph.setdefault(dependency.predecessor_task_id, []).append(dependency.successor_task_id)
        graph.setdefault(predecessor_id, []).append(successor_id)

        target = predecessor_id
        stack = [successor_id]
        visited = set()

        while stack:
            current = stack.pop()
            if current == target:
                raise BusinessRuleError(
                    "Adding this dependency would create a circular dependency.",
                    code="DEPENDENCY_CYCLE",
                )
            if current in visited:
                continue
            visited.add(current)
            for nxt in graph.get(current, []):
                if nxt not in visited:
                    stack.append(nxt)

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
