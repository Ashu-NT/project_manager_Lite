"""Permission-scoped Task dependency reads."""

from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import TaskDependency
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.domain.security.auth.session import UserSessionContext


class TaskDependencyQueryHandler:
    def __init__(
        self,
        *,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        user_session: UserSessionContext | None,
    ) -> None:
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._user_session = user_session

    def get_dependency(self, dep_id: str) -> TaskDependency | None:
        require_permission(self._user_session, "task.read", operation_label="view dependency")
        dependency = self._dependency_repo.get(dep_id)
        if dependency is None:
            return None
        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "task.read",
                operation_label="view dependency",
            )
        return dependency

    def list_dependencies_for_task(self, task_id: str) -> list[TaskDependency]:
        require_permission(self._user_session, "task.read", operation_label="list task dependencies")
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="list task dependencies",
        )
        return self._dependency_repo.list_by_task(task_id)

    def list_dependencies_for_project(self, project_id: str) -> list[TaskDependency]:
        """Use the project-wide repository query rather than an N+1 task loop."""
        require_permission(self._user_session, "task.read", operation_label="list project dependencies")
        require_project_permission(
            self._user_session,
            project_id,
            "task.read",
            operation_label="list project dependencies",
        )
        return self._dependency_repo.list_by_project(project_id)


__all__ = ["TaskDependencyQueryHandler"]
