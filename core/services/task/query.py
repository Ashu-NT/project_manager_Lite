from __future__ import annotations

from datetime import date
from typing import List

from core.exceptions import ValidationError
from core.interfaces import AssignmentRepository, TaskRepository
from core.models import Task, TaskAssignment, TaskStatus


class TaskQueryMixin:
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository

    def list_tasks_for_project(self, project_id: str) -> List[Task]:
        return self._task_repo.list_by_project(project_id)

    def list_tasks_for_resource(self, resource_id: str) -> List[Task]:
        assignments = self._assignment_repo.list_by_resource(resource_id)
        task_ids = {a.task_id for a in assignments}
        tasks: List[Task] = []
        for tid in task_ids:
            t = self._task_repo.get(tid)
            if t:
                tasks.append(t)
        return tasks

    def list_assignments_for_tasks(self, task_ids: list[str]) -> List[TaskAssignment]:
        if not task_ids:
            return []
        return self._assignment_repo.list_by_tasks(task_ids)

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
        if project_id:
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
