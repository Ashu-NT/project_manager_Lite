from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency


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


class AssignmentRepository(ABC):
    @abstractmethod
    def add(self, assignment: TaskAssignment) -> None: ...

    @abstractmethod
    def get(self, assignment_id: str) -> TaskAssignment | None: ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> list[TaskAssignment]: ...

    @abstractmethod
    def list_by_resource(self, resource_id: str) -> list[TaskAssignment]: ...

    @abstractmethod
    def update(self, assignment: TaskAssignment) -> None: ...

    @abstractmethod
    def delete(self, assignment_id: str) -> None: ...

    @abstractmethod
    def delete_by_task(self, task_id: str) -> None: ...

    @abstractmethod
    def list_by_assignment(self, task_id: str) -> list[TaskAssignment]: ...

    @abstractmethod
    def list_by_tasks(self, task_ids: list[str]) -> list[TaskAssignment]: ...


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
