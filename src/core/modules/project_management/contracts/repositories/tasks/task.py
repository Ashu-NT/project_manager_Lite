from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency


@dataclass(frozen=True, slots=True)
class TimesheetAssignmentContext:
    assignment_id: str
    project_id: str
    project_name: str
    task_id: str
    task_name: str
    resource_id: str
    resource_name: str


class TaskRepository(ABC):
    @abstractmethod
    def add(self, task: Task) -> None: ...

    @abstractmethod
    def update(self, task: Task) -> None: ...

    @abstractmethod
    def delete(self, task_id: str) -> None: ...

    @abstractmethod
    def get(self, task_id: str) -> Task | None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> list[Task]: ...

    @abstractmethod
    def list_children(self, project_id: str, parent_task_id: str | None) -> list[Task]: ...


class AssignmentRepository(ABC):
    @abstractmethod
    def add(self, assignment: TaskAssignment) -> None: ...

    @abstractmethod
    def get(self, assignment_id: str) -> TaskAssignment | None: ...

    @abstractmethod
    def list_by_ids(self, assignment_ids: list[str]) -> list[TaskAssignment]:
        """Batch fetch by assignment id -- the WorkAllocationRepository-side
        counterpart callers must use instead of calling get() in a loop."""
        ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> list[TaskAssignment]: ...

    @abstractmethod
    def list_by_resource(self, resource_id: str) -> list[TaskAssignment]: ...

    @abstractmethod
    def update(self, assignment: TaskAssignment) -> None: ...

    @abstractmethod
    def update_planned_hours_with_version_check(
        self, assignment: TaskAssignment, *, expected_version: int
    ) -> TaskAssignment:
        """Dedicated, versioned write path for
        ``allocated_planned_hours``"""
        ...

    @abstractmethod
    def update_allocation_with_version_check(
        self, assignment: TaskAssignment, *, expected_version: int
    ) -> TaskAssignment:
        """Dedicated, versioned write path for ``allocation_percent``."""
        ...

    @abstractmethod
    def delete(self, assignment_id: str) -> None: ...

    @abstractmethod
    def delete_by_task(self, task_id: str) -> None: ...

    @abstractmethod
    def list_by_assignment(self, task_id: str) -> list[TaskAssignment]: ...

    @abstractmethod
    def list_by_tasks(self, task_ids: list[str]) -> list[TaskAssignment]: ...

    @abstractmethod
    def list_timesheet_contexts(
        self,
        *,
        project_id: str | None = None,
        assignment_id: str | None = None,
    ) -> list[TimesheetAssignmentContext]: ...


class DependencyRepository(ABC):
    @abstractmethod
    def add(self, dependency: TaskDependency) -> None: ...

    @abstractmethod
    def get(self, dependency_id: str) -> TaskDependency | None: ...

    @abstractmethod
    def update(self, dependency: TaskDependency) -> None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> list[TaskDependency]: ...

    @abstractmethod
    def delete(self, dependency_id: str) -> None: ...

    @abstractmethod
    def delete_for_task(self, task_id: str) -> None: ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> list[TaskDependency]: ...
