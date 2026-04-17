from __future__ import annotations

from datetime import date
from typing import List

from core.platform.common.exceptions import ValidationError
from core.modules.project_management.interfaces import AssignmentRepository, TaskRepository
from core.modules.project_management.domain.task import Task, TaskAssignment
from core.modules.project_management.domain.enums import TaskStatus
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission


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
        task_ids = {a.task_id for a in assignments}
        tasks: List[Task] = []
        for tid in task_ids:
            t = self._task_repo.get(tid)
            if t and self._user_session.has_project_permission(t.project_id, "task.read"):
                tasks.append(t)
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
            tasks = [t for t in tasks if t.status == status]

        if start_from:
            tasks = [t for t in tasks if t.start_date and t.start_date >= start_from]
        if start_to:
            tasks = [t for t in tasks if t.start_date and t.start_date <= start_to]
        if end_from:
            tasks = [t for t in tasks if t.end_date and t.end_date >= end_from]
        if end_to:
            tasks = [t for t in tasks if t.end_date and t.end_date <= end_to]

        if resource_id:
            assignments = self._assignment_repo.list_by_resource(resource_id)
            task_ids = {a.task_id for a in assignments}
            tasks = [t for t in tasks if t.id in task_ids]

        return tasks
