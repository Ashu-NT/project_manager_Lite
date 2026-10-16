from datetime import date, timedelta

from src.core.modules.project_management.application.tasks._command_values import (
    constraint_type as constraint_type_value,
)
from src.core.modules.project_management.application.tasks._command_values import (
    task_status,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_constraints import (
    TaskConstraintUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_dependencies import (
    TaskDependencyCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_hierarchy import (
    TaskWbsMoveCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
    TaskUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_progress import (
    TaskBulkStatusCommand,
    TaskProgressCommand,
)
from src.core.modules.project_management.application.tasks.dto.responses.assignment import (
    TaskAssignmentResponseDto,
)
from src.core.modules.project_management.application.tasks.dto.responses.dependency import (
    TaskDependencyResponseDto,
)
from src.core.modules.project_management.application.tasks.dto.responses.task import (
    TaskResponseDto,
)
from src.core.modules.project_management.application.tasks.mappers.assignment import (
    map_assignment,
)
from src.core.modules.project_management.application.tasks.mappers.dependency import (
    map_dependency,
    map_dependency_read_item,
)
from src.core.modules.project_management.application.tasks.mappers.task import map_task
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
    def query_task_responses(self, project_id: str) -> tuple[TaskResponseDto, ...]:
        return tuple(map_task(task, project_name="") for task in self.list_tasks_for_project(project_id))

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._assignments: dict[str, TaskAssignment] = {}
        self._dependencies: dict[str, TaskDependency] = {}
        self._project_resource_lookup: dict[str, str] = {}
        self._next_id = 1

    def _assignment_response(self, assignment, *, with_context=False):
        context_method = getattr(self, "get_assignment_action_context", None)
        context = context_method(assignment.id) if with_context and context_method is not None else None
        return map_assignment(
            assignment, resource_name=getattr(self, "_resource_names", {}).get(assignment.resource_id, assignment.resource_id),
            can_manage=bool(getattr(context, "can_manage", False)),
            can_accept=bool(getattr(context, "can_accept", False)),
            can_decline=bool(getattr(context, "can_decline", False)),
        )

    def query_assignment_responses(self, task_id):
        return tuple(self._assignment_response(row, with_context=True) for row in self.list_assignments_for_task(task_id))

    def query_dependency_responses(self, task_id):
        return tuple(map_dependency_read_item(edge, task_id=task_id, tasks_by_id=self._tasks)
                     for edge in self.list_dependencies_for_task(task_id))

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def register_project_resource(self, project_resource_id: str, resource_id: str, resource_name: str = "") -> None:
        self._project_resource_lookup[project_resource_id] = resource_id
        if not hasattr(self, "_resource_names"):
            self._resource_names = {}
        self._resource_names[resource_id] = resource_name or resource_id

    def create_task(self, command: TaskCreateCommand) -> TaskResponseDto:
        project_id = command.project_id
        name = command.name
        code = command.code
        description = command.description
        start_date = command.start_date
        duration_days = command.duration_days
        priority = command.priority if command.priority is not None else 0
        deadline = command.deadline
        parent_task_id = command.parent_task_id
        wbs_code = command.wbs_code
        sort_order = command.sort_order
        is_milestone = command.is_milestone
        constraint_type = constraint_type_value(command.constraint_type)
        constraint_date = command.constraint_date
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
        self.set_tasks_status(TaskBulkStatusCommand((task.id,), command.status))
        return map_task(task, project_name="")

    def move_task(self, command: TaskWbsMoveCommand) -> TaskResponseDto:
        task_id = command.task_id
        parent_task_id = command.parent_task_id
        wbs_code = command.wbs_code
        sort_order = command.sort_order
        expected_version = command.expected_version
        task = self._tasks[task_id]
        if expected_version is not None and task.version != expected_version:
            raise ValueError("Task version is stale.")
        task.parent_task_id = parent_task_id
        if wbs_code:
            task.wbs_code = wbs_code
        if sort_order is not None:
            task.sort_order = sort_order
        task.version += 1
        return map_task(task, project_name="")

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

    def assign_project_resource(self, command: TaskAssignmentCreateCommand) -> TaskAssignmentResponseDto:
        task_id = command.task_id
        project_resource_id = command.project_resource_id
        allocation_percent = command.allocation_percent
        allocated_planned_hours = command.allocated_planned_hours
        resource_id = self._project_resource_lookup.get(project_resource_id, project_resource_id)
        assignment = self.create_assignment(
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
        )
        assignment.project_resource_id = project_resource_id
        if allocated_planned_hours is not None:
            assignment.allocated_planned_hours = allocated_planned_hours
        return self._assignment_response(assignment)

    def set_assignment_allocation(self, command: TaskAssignmentAllocationCommand) -> TaskAssignmentResponseDto:
        assignment_id = command.assignment_id
        allocation_percent = command.allocation_percent
        expected_version = command.expected_version
        assignment = self._assignments[assignment_id]
        assignment.allocation_percent = allocation_percent
        if expected_version is not None:
            assignment.version = expected_version + 1
        return self._assignment_response(assignment)

    def set_assignment_hours(self, command: TaskAssignmentHoursCommand) -> TaskAssignmentResponseDto:
        assignment_id = command.assignment_id
        hours_logged = command.hours_logged
        assignment = self._assignments[assignment_id]
        assignment.hours_logged = hours_logged
        return self._assignment_response(assignment)

    def unassign_resource(self, assignment_id: str) -> None:
        del self._assignments[assignment_id]

    def add_dependency(self, command: TaskDependencyCreateCommand) -> TaskDependencyResponseDto:
        predecessor_id = command.linked_task_id if command.relationship_direction.strip().upper() == "PREDECESSOR" else command.task_id
        successor_id = command.task_id if command.relationship_direction.strip().upper() == "PREDECESSOR" else command.linked_task_id
        dependency_type = DependencyType(command.dependency_type)
        lag_days = command.lag_days
        dependency = TaskDependency(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )
        self._dependencies[dependency.id] = dependency
        return map_dependency(dependency)

    def list_dependencies_for_task(self, task_id: str) -> list[TaskDependency]:
        return [
            d for d in self._dependencies.values()
            if d.predecessor_task_id == task_id or d.successor_task_id == task_id
        ]

    def remove_dependency(self, dependency_id: str) -> None:
        del self._dependencies[dependency_id]

    def update_task(self, command: TaskUpdateCommand) -> TaskResponseDto:
        task_id = command.task_id
        expected_version = command.expected_version
        name = command.name
        code = command.code
        description = command.description
        status = task_status(command.status)
        start_date = command.start_date
        duration_days = command.duration_days
        priority = command.priority
        deadline = command.deadline
        is_milestone = command.is_milestone
        task = self._tasks[task_id]
        if expected_version is not None:
            assert task.version == expected_version
        if name is not None:
            task.name = name
        if code is not None and code:
            task.code = code
        if description is not None:
            task.description = description
        if status is not None:
            self.set_tasks_status(TaskBulkStatusCommand((task.id,), status.value))
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
        return map_task(task, project_name="")

    def update_task_scheduling_constraint(self, command: TaskConstraintUpdateCommand) -> TaskResponseDto:
        task_id = command.task_id
        constraint_type = constraint_type_value(command.constraint_type)
        constraint_date = command.constraint_date
        expected_version = command.expected_version
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
        return map_task(updated, project_name="")

    def _set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def set_tasks_status(self, command: TaskBulkStatusCommand) -> list[TaskResponseDto]:
        task_ids = command.task_ids
        status = task_status(command.status)
        reopen_percent_complete = command.reopen_percent_complete
        changed: list[Task] = []
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            if task.status == status:
                continue
            if reopen_percent_complete is not None and status == TaskStatus.IN_PROGRESS:
                task.percent_complete = reopen_percent_complete
            self._set_status(task_id, status)
            changed.append(task)
        return [map_task(task, project_name="") for task in changed]

    def update_progress(self, command: TaskProgressCommand) -> TaskResponseDto:
        task_id = command.task_id
        percent_complete = command.percent_complete
        actual_start = command.actual_start
        actual_end = command.actual_end
        status = task_status(command.status) if command.status is not None else None
        expected_version = command.expected_version
        task = self._tasks[task_id]
        if expected_version is not None:
            assert task.version == expected_version
        if percent_complete is not None:
            task.percent_complete = percent_complete
        if actual_start is not None:
            task.actual_start = actual_start
        if actual_end is not None:
            task.actual_end = actual_end
        if status is not None:
            task.status = status
        task.version += 1
        return map_task(task, project_name="")

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

    def list_tasks_by_ids(self, task_ids: list[str]) -> list[Task]:
        return [self._tasks[task_id] for task_id in task_ids if task_id in self._tasks]


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
