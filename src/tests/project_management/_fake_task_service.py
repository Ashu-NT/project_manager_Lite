from datetime import date, timedelta

from src.core.modules.project_management.domain.enums import (
    DependencyType,
    TaskStatus,
)
from src.core.modules.project_management.domain.tasks.task import (
    Task,
    TaskAssignment,
    TaskDependency,
)


class _FakeTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._assignments: dict[str, TaskAssignment] = {}
        self._dependencies: dict[str, TaskDependency] = {}
        self._project_resource_lookup: dict[str, str] = {}
        self._next_id = 1

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def register_project_resource(self, project_resource_id: str, resource_id: str) -> None:
        self._project_resource_lookup[project_resource_id] = resource_id

    def create_task(
        self,
        *,
        project_id: str,
        name: str,
        code: str = "",
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int = 0,
        deadline: date | None = None,
        parent_task_id: str | None = None,
        wbs_code: str = "",
        sort_order: int | None = None,
        is_milestone: bool = False,
        constraint_type=None,
        constraint_date: date | None = None,
    ) -> Task:
        resolved_sort_order = (
            sort_order
            if sort_order is not None
            else len(
                [
                    task
                    for task in self._tasks.values()
                    if task.project_id == project_id
                    and task.parent_task_id == parent_task_id
                ]
            )
        )
        task = Task(
            id=f"task-{self._next_id}",
            project_id=project_id,
            name=name,
            code=code,
            description=description,
            start_date=start_date,
            end_date=_derive_end_date(start_date, duration_days),
            duration_days=duration_days,
            priority=priority,
            deadline=deadline,
            parent_task_id=parent_task_id,
            wbs_code=wbs_code or str(self._next_id),
            sort_order=resolved_sort_order,
            is_milestone=is_milestone,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
        )
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def move_task(
        self,
        task_id: str,
        *,
        parent_task_id: str | None,
        wbs_code: str | None = None,
        sort_order: int | None = None,
        expected_version: int | None = None,
    ) -> Task:
        task = self._tasks[task_id]
        if expected_version is not None and task.version != expected_version:
            raise ValueError("Task version is stale.")
        task.parent_task_id = parent_task_id
        if wbs_code:
            task.wbs_code = wbs_code
        if sort_order is not None:
            task.sort_order = sort_order
        task.version += 1
        return task

    def create_assignment(
        self,
        *,
        task_id: str,
        resource_id: str,
        allocation_percent: float = 100.0,
        hours_logged: float = 0.0,
    ) -> TaskAssignment:
        assignment = TaskAssignment(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
            hours_logged=hours_logged,
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def list_assignments_for_task(self, task_id: str) -> list[TaskAssignment]:
        return [a for a in self._assignments.values() if a.task_id == task_id]

    def list_assignments_for_tasks(self, task_ids: list[str]) -> list[TaskAssignment]:
        task_id_set = {str(tid) for tid in task_ids}
        return [a for a in self._assignments.values() if a.task_id in task_id_set]

    def get_assignment(self, assignment_id: str) -> TaskAssignment | None:
        return self._assignments.get(assignment_id)

    def assign_project_resource(
        self,
        *,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
        allocated_planned_hours=None,
    ) -> TaskAssignment:
        resource_id = self._project_resource_lookup.get(project_resource_id, project_resource_id)
        assignment = self.create_assignment(
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
        )
        assignment.project_resource_id = project_resource_id
        if allocated_planned_hours is not None:
            assignment.allocated_planned_hours = allocated_planned_hours
        return assignment

    def set_assignment_allocation(
        self, *, assignment_id: str, allocation_percent: float, expected_version: int | None = None
    ) -> TaskAssignment:
        assignment = self._assignments[assignment_id]
        assignment.allocation_percent = allocation_percent
        if expected_version is not None:
            assignment.version = expected_version + 1
        return assignment

    def set_assignment_hours(self, *, assignment_id: str, hours_logged: float) -> TaskAssignment:
        assignment = self._assignments[assignment_id]
        assignment.hours_logged = hours_logged
        return assignment

    def unassign_resource(self, assignment_id: str) -> None:
        del self._assignments[assignment_id]

    def add_dependency(
        self,
        *,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType,
        lag_days: int = 0,
    ) -> TaskDependency:
        dependency = TaskDependency(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )
        self._dependencies[dependency.id] = dependency
        return dependency

    def list_dependencies_for_task(self, task_id: str) -> list[TaskDependency]:
        return [
            d for d in self._dependencies.values()
            if d.predecessor_task_id == task_id or d.successor_task_id == task_id
        ]

    def remove_dependency(self, dependency_id: str) -> None:
        del self._dependencies[dependency_id]

    def update_task(
        self,
        task_id: str,
        *,
        expected_version: int | None = None,
        name: str | None = None,
        code: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int | None = None,
        deadline: date | None = None,
        is_milestone: bool | None = None,
    ) -> Task:
        task = self._tasks[task_id]
        if name is not None:
            task.name = name
        if code is not None and code:
            task.code = code
        if description is not None:
            task.description = description
        if status is not None:
            task.status = status
        if start_date is not None:
            task.start_date = start_date
        if duration_days is not None:
            task.duration_days = duration_days
        if priority is not None:
            task.priority = priority
        if deadline is not None:
            task.deadline = deadline
        if is_milestone is not None:
            task.is_milestone = is_milestone
        if task.is_milestone:
            task.duration_days = 0
        task.end_date = _derive_end_date(task.start_date, task.duration_days)
        task.version += 1
        return task

    def update_task_scheduling_constraint(
        self,
        task_id: str,
        *,
        constraint_type=None,
        constraint_date: date | None = None,
        expected_version: int | None = None,
    ) -> Task:
        task = self._tasks[task_id]
        if expected_version is not None and task.version != expected_version:
            from src.core.platform.common.exceptions import ConcurrencyError

            raise ConcurrencyError("Task was updated by another user.", code="STALE_WRITE")
        # One atomic replace(), not sequential attribute assignment --
        # see the note on _task() in test_constraint_validator.py for why
        # (validate_assignment=True re-runs the whole model validator per
        # set, and "dated constraint requires a date" would spuriously
        # fire between the two assignments otherwise).
        from dataclasses import replace

        updated = replace(task, constraint_type=constraint_type, constraint_date=constraint_date)
        updated.version = task.version + 1
        self._tasks[task_id] = updated
        return updated

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def set_tasks_status(
        self,
        task_ids: tuple[str, ...],
        status: TaskStatus,
        *,
        reopen_percent_complete: float | None = None,
    ) -> list[Task]:
        changed: list[Task] = []
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            if task.status == status:
                continue
            if reopen_percent_complete is not None and status == TaskStatus.IN_PROGRESS:
                task.percent_complete = reopen_percent_complete
            self.set_status(task_id, status)
            changed.append(task)
        return changed

    def update_progress(
        self,
        task_id: str,
        *,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> Task:
        task = self._tasks[task_id]
        if percent_complete is not None:
            task.percent_complete = percent_complete
        if actual_start is not None:
            task.actual_start = actual_start
        if actual_end is not None:
            task.actual_end = actual_end
        if status is not None:
            task.status = status
        task.version += 1
        return task

    def delete_task(self, task_id: str) -> None:
        del self._tasks[task_id]

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        deleted: list[str] = []
        for task_id in task_ids:
            if task_id in self._tasks:
                self.delete_task(task_id)
                deleted.append(task_id)
        return tuple(deleted)

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
