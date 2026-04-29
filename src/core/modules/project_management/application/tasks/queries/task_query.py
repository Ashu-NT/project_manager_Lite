from __future__ import annotations

from datetime import date
from typing import List

from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ValidationError
from src.src.core.modules.project_management.domain.enums import TaskStatus


class TaskQueryMixin:
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository

    def get_task(self, task_id: str) -> Task | None:
        require_permission(self._user_session, "task.read", operation_label="view task")
        task = self._task_repo.get(task_id)
        if task is None:
            return None
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="view task",
        )
        return task

    def list_tasks_for_project(self, project_id: str) -> List[Task]:
        require_permission(self._user_session, "task.read", operation_label="list project tasks")
        require_project_permission(
            self._user_session,
            project_id,
            "task.read",
            operation_label="list project tasks",
        )
        return self._task_repo.list_by_project(project_id)

    def list_tasks_for_resource(self, resource_id: str) -> List[Task]:
        require_permission(self._user_session, "task.read", operation_label="list resource tasks")
        assignments = self._assignment_repo.list_by_resource(resource_id)
        task_ids = {assignment.task_id for assignment in assignments}
        tasks: List[Task] = []
        for task_id in task_ids:
            task = self._task_repo.get(task_id)
            if task and self._user_session.has_project_permission(task.project_id, "task.read"):
                tasks.append(task)
        return tasks

    def list_assignments_for_tasks(self, task_ids: list[str]) -> List[TaskAssignment]:
        require_permission(self._user_session, "task.read", operation_label="list task assignments")
        if not task_ids:
            return []
        allowed_ids: list[str] = []
        for task_id in task_ids:
            task = self._task_repo.get(task_id)
            if task is None:
                continue
            if self._user_session.has_project_permission(task.project_id, "task.read"):
                allowed_ids.append(task_id)
        return self._assignment_repo.list_by_tasks(allowed_ids)

    def query_tasks(
        self,
        project_id: str | None = None,
        status: TaskStatus | None = None,
        resource_id: str | None = None,
        start_from: date | None = None,
        start_to: date | None = None,
        end_from: date | None = None,
        end_to: date | None = None,
    ) -> List[Task]:
        require_permission(self._user_session, "task.read", operation_label="query tasks")
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "task.read",
                operation_label="query tasks",
            )
            tasks = self._task_repo.list_by_project(project_id)
        else:
            raise ValidationError("project_id is required for query_tasks currently.")

        if status:
            tasks = [task for task in tasks if task.status == status]

        if start_from:
            tasks = [task for task in tasks if task.start_date and task.start_date >= start_from]
        if start_to:
            tasks = [task for task in tasks if task.start_date and task.start_date <= start_to]
        if end_from:
            tasks = [task for task in tasks if task.end_date and task.end_date >= end_from]
        if end_to:
            tasks = [task for task in tasks if task.end_date and task.end_date <= end_to]

        if resource_id:
            assignments = self._assignment_repo.list_by_resource(resource_id)
            task_ids = {assignment.task_id for assignment in assignments}
            tasks = [task for task in tasks if task.id in task_ids]

        return tasks


__all__ = ["TaskQueryMixin"]


