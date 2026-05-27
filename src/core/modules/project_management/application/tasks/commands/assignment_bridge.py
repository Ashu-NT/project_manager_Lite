from __future__ import annotations

from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.modules.project_management.domain.tasks.task import TaskAssignment
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class TaskAssignmentBridgeMixin:
    def assign_resource(
        self, task_id: str, resource_id: str, allocation_percent: float = 100.0
    ) -> TaskAssignment:
        self._require_manage("add assignment")
        alloc = float(allocation_percent or 0.0)
        if alloc <= 0 or alloc > 100:
            raise ValidationError("allocation_percent must be > 0 and <= 100.")

        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")

        if not self._project_resource_repo:
            self._check_resource_overallocation(
                project_id=task.project_id,
                resource_id=resource_id,
                new_task_id=task_id,
                new_alloc_percent=alloc,
            )
            assignment = TaskAssignment.create(task_id, resource_id, alloc)
            try:
                self._assignment_repo.add(assignment)
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise
            self._emit_tasks_changed(task.project_id)
            return assignment

        project_resource = self._project_resource_repo.get_for_project(task.project_id, resource_id)
        if not project_resource:
            project_resource = ProjectResource.create(
                project_id=task.project_id,
                resource_id=resource_id,
                hourly_rate=getattr(resource, "hourly_rate", None),
                currency_code=getattr(resource, "currency_code", None),
                planned_hours=0.0,
                is_active=bool(getattr(resource, "is_active", True)),
            )
            try:
                self._project_resource_repo.add(project_resource)
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise

        return self.assign_project_resource(
            task_id=task_id,
            project_resource_id=project_resource.id,
            allocation_percent=alloc,
        )

    @staticmethod
    def _emit_tasks_changed(project_id: str) -> None:
        from src.core.platform.notifications.domain_events import domain_events

        domain_events.tasks_changed.emit(project_id)


__all__ = ["TaskAssignmentBridgeMixin"]
