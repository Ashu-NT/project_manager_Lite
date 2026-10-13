from __future__ import annotations

from typing import cast

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
    TimesheetAssignmentContext,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class TaskLookupQueryHandler:
    """Scoped task and assignment lookups for current application callers."""

    def __init__(
        self,
        *,
        task_repo: TaskRepository,
        assignment_repo: AssignmentRepository,
        user_session: UserSessionContext | None,
    ) -> None:
        self._task_repo = task_repo
        self._assignment_repo = assignment_repo
        self._user_session = user_session

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        require_permission(
            self._user_session, "task.read", operation_label="list project tasks"
        )
        require_project_permission(
            self._user_session,
            project_id,
            "task.read",
            operation_label="list project tasks",
        )
        return self._task_repo.list_by_project(project_id)

    def list_tasks_for_resource(self, resource_id: str) -> list[Task]:
        require_permission(
            self._user_session, "task.read", operation_label="list resource tasks"
        )
        session = cast(UserSessionContext, self._user_session)
        assignments = self._assignment_repo.list_by_resource(resource_id)
        task_ids = list(dict.fromkeys(assignment.task_id for assignment in assignments))
        tasks_by_id = {task.id: task for task in self._task_repo.list_by_ids(task_ids)}
        tasks: list[Task] = []
        for task_id in task_ids:
            task = tasks_by_id.get(task_id)
            if task and session.has_project_permission(task.project_id, "task.read"):
                tasks.append(task)
        return tasks

    def list_assignments_for_resource(self, resource_id: str) -> list[TaskAssignment]:
        require_permission(
            self._user_session,
            "task.read",
            operation_label="list resource assignments",
        )
        session = cast(UserSessionContext, self._user_session)
        assignments = self._assignment_repo.list_by_resource(resource_id)
        tasks_by_id = {
            task.id: task
            for task in self._task_repo.list_by_ids(
                list(dict.fromkeys(assignment.task_id for assignment in assignments))
            )
        }
        allowed: list[TaskAssignment] = []
        for assignment in assignments:
            task = tasks_by_id.get(assignment.task_id)
            if task and session.has_project_permission(task.project_id, "task.read"):
                allowed.append(assignment)
        return allowed

    def list_assignments_for_tasks(self, task_ids: list[str]) -> list[TaskAssignment]:
        require_permission(
            self._user_session, "task.read", operation_label="list task assignments"
        )
        session = cast(UserSessionContext, self._user_session)
        if not task_ids:
            return []
        tasks_by_id = {
            task.id: task
            for task in self._task_repo.list_by_ids(list(dict.fromkeys(task_ids)))
        }
        allowed_ids: list[str] = []
        for task_id in dict.fromkeys(task_ids):
            task = tasks_by_id.get(task_id)
            if task is None:
                continue
            if session.has_project_permission(task.project_id, "task.read"):
                allowed_ids.append(task_id)
        return self._assignment_repo.list_by_tasks(allowed_ids)

    def list_timesheet_assignment_contexts(
        self,
        *,
        project_id: str | None = None,
        resource_id: str | None = None,
    ) -> list[TimesheetAssignmentContext]:
        require_permission(
            self._user_session,
            "task.read",
            operation_label="list timesheet assignments",
        )
        session = cast(UserSessionContext, self._user_session)
        normalized_project_id = str(project_id or "").strip() or None
        if normalized_project_id is not None:
            require_project_permission(
                self._user_session,
                normalized_project_id,
                "task.read",
                operation_label="list timesheet assignments",
            )
        rows = self._assignment_repo.list_timesheet_contexts(
            project_id=normalized_project_id,
            resource_id=str(resource_id or "").strip() or None,
        )
        if normalized_project_id is not None:
            return rows
        return [
            row
            for row in rows
            if session.has_project_permission(row.project_id, "task.read")
        ]

    def get_timesheet_assignment_context(
        self,
        assignment_id: str,
    ) -> TimesheetAssignmentContext | None:
        require_permission(
            self._user_session,
            "task.read",
            operation_label="view timesheet assignment",
        )
        rows = self._assignment_repo.list_timesheet_contexts(
            assignment_id=str(assignment_id or "").strip()
        )
        if not rows:
            return None
        row = rows[0]
        require_project_permission(
            self._user_session,
            row.project_id,
            "task.read",
            operation_label="view timesheet assignment",
        )
        return row


__all__ = ["TaskLookupQueryHandler"]
