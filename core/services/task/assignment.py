from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from core.events.domain_events import domain_events
from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.interfaces import (
    AssignmentRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TaskRepository,
)
from core.models import ProjectResource, TaskAssignment


class TaskAssignmentMixin:
    _session: Session
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _project_resource_repo: ProjectResourceRepository | None

    def unassign_resource(self, assignment_id: str) -> None:
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(assignment.task_id)
        try:
            self._assignment_repo.delete(assignment_id)
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            raise exc
        if task:
            domain_events.tasks_changed.emit(task.project_id)

    def list_assignments_for_task(self, task_id: str) -> List[TaskAssignment]:
        return self._assignment_repo.list_by_assignment(task_id)

    def set_assignment_hours(self, assignment_id: str, hours_logged: float) -> TaskAssignment:
        if hours_logged < 0:
            raise ValidationError("hours_logged cannot be negative.")
        a = self._assignment_repo.get(assignment_id)
        if not a:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(a.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        a.hours_logged = hours_logged
        try:
            self._assignment_repo.update(a)
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            raise exc
        domain_events.tasks_changed.emit(task.project_id)
        return a

    def get_assignment(self, assignment_id: str) -> TaskAssignment | None:
        return self._assignment_repo.get(assignment_id)

    def assign_project_resource(
        self, task_id: str, project_resource_id: str, allocation_percent: float
    ) -> TaskAssignment:
        if not self._project_resource_repo:
            raise BusinessRuleError(
                "Project resource repository is not configured.",
                code="PROJECT_RESOURCE_REPO_MISSING",
            )

        alloc = float(allocation_percent or 0.0)
        if alloc <= 0 or alloc > 100:
            raise ValidationError("allocation_percent must be > 0 and <= 100.")

        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        pr = self._project_resource_repo.get(project_resource_id)
        if not pr:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")

        if pr.project_id != task.project_id:
            raise BusinessRuleError(
                "Selected resource is not linked to this task's project.",
                code="PROJECT_RESOURCE_MISMATCH",
            )

        if not getattr(pr, "is_active", True):
            raise BusinessRuleError("This project resource is inactive.", code="PROJECT_RESOURCE_INACTIVE")

        self._check_resource_overallocation(
            project_id=task.project_id,
            resource_id=pr.resource_id,
            new_task_id=task.id,
            new_alloc_percent=alloc,
        )

        assignment = TaskAssignment.create(task_id, pr.resource_id, alloc)
        setattr(assignment, "project_resource_id", pr.id)

        try:
            self._assignment_repo.add(assignment)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        domain_events.tasks_changed.emit(task.project_id)
        return assignment

    def assign_resource(
        self, task_id: str, resource_id: str, allocation_percent: float = 100.0
    ) -> TaskAssignment:
        alloc = float(allocation_percent or 0.0)
        if alloc <= 0 or alloc > 100:
            raise ValidationError("allocation_percent must be > 0 and <= 100.")

        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        res = self._resource_repo.get(resource_id)
        if not res:
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
            domain_events.tasks_changed.emit(task.project_id)
            return assignment

        pr = self._project_resource_repo.get_for_project(task.project_id, resource_id)
        if not pr:
            pr = ProjectResource.create(
                project_id=task.project_id,
                resource_id=resource_id,
                hourly_rate=getattr(res, "hourly_rate", None),
                currency_code=getattr(res, "currency_code", None),
                planned_hours=0.0,
                is_active=bool(getattr(res, "is_active", True)),
            )
            try:
                self._project_resource_repo.add(pr)
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise

        return self.assign_project_resource(
            task_id=task_id,
            project_resource_id=pr.id,
            allocation_percent=alloc,
        )
