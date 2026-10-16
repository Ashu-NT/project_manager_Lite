from datetime import date
from types import SimpleNamespace

from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
    TaskAssignmentCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_dependencies import (
    TaskDependencyCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_progress import (
    TaskProgressCommand,
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


class _FakeTaskService:
    def query_task_responses(self, project_id):
        return tuple(map_task(task, project_name="") for task in self.list_tasks_for_project(project_id))

    def __init__(self, tasks: list[SimpleNamespace] | None = None) -> None:
        self._tasks = {
            task.id: task
            for task in (tasks or [])
        }
        self._assignments: dict[str, SimpleNamespace] = {}
        self._dependencies: dict[str, SimpleNamespace] = {}
        self._project_resource_lookup: dict[str, str] = {}

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

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [
            task
            for task in self._tasks.values()
            if task.project_id == project_id
        ]

    def get_task(self, task_id: str) -> SimpleNamespace | None:
        return self._tasks.get(task_id)

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def update_progress(self, command: TaskProgressCommand):
        task_id = command.task_id
        percent_complete = command.percent_complete
        actual_start = command.actual_start
        actual_end = command.actual_end
        status = TaskStatus(command.status) if command.status is not None else None
        task = self._tasks[task_id]
        if percent_complete is not None:
            task.percent_complete = float(percent_complete)
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

    def register_project_resource(self, project_resource_id: str, resource_id: str, resource_name: str = "") -> None:
        self._project_resource_lookup[project_resource_id] = resource_id
        if not hasattr(self, "_resource_names"):
            self._resource_names = {}
        self._resource_names[resource_id] = resource_name or resource_id

    def list_assignments_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [
            assignment
            for assignment in self._assignments.values()
            if assignment.task_id == task_id
        ]

    def assign_project_resource(self, command: TaskAssignmentCreateCommand):
        task_id = command.task_id
        project_resource_id = command.project_resource_id
        allocation_percent = command.allocation_percent
        assignment = SimpleNamespace(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=self._project_resource_lookup.get(
                project_resource_id,
                project_resource_id,
            ),
            allocation_percent=allocation_percent,
            hours_logged=0.0,
            project_resource_id=project_resource_id,
        )
        self._assignments[assignment.id] = assignment
        return self._assignment_response(assignment)

    def add_dependency(self, command: TaskDependencyCreateCommand):
        predecessor_id = command.linked_task_id if command.relationship_direction.upper() == "PREDECESSOR" else command.task_id
        successor_id = command.task_id if command.relationship_direction.upper() == "PREDECESSOR" else command.linked_task_id
        dependency_type = command.dependency_type
        lag_days = command.lag_days
        dependency = SimpleNamespace(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=DependencyType(str(dependency_type)),
            lag_days=lag_days,
        )
        self._dependencies[dependency.id] = dependency
        return map_dependency(dependency)

    def list_dependencies_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [
            dependency
            for dependency in self._dependencies.values()
            if dependency.predecessor_task_id == task_id
            or dependency.successor_task_id == task_id
        ]


class _FakeTaskOptionService:
    def __init__(self, tasks_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._tasks_by_project = tasks_by_project

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._tasks_by_project.get(project_id, []))


def _build_task_record(
    *,
    task_id: str,
    project_id: str,
    name: str,
    description: str,
    status: TaskStatus,
    start_date: date | None,
    end_date: date | None,
    duration_days: int | None,
    priority: int,
    percent_complete: float,
    deadline: date | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id,
        project_id=project_id,
        name=name,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        priority=priority,
        percent_complete=percent_complete,
        actual_start=None,
        actual_end=None,
        deadline=deadline,
        version=1,
    )
