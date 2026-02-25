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
from core.models import TaskAssignment
from core.services.auth.authorization import require_permission
from core.services.task.assignment_audit import record_assignment_action


class TaskAssignmentMixin:
    _session: Session
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _project_resource_repo: ProjectResourceRepository | None

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "task.manage", operation_label=operation_label)

    def unassign_resource(self, assignment_id: str) -> None:
        self._require_manage("remove assignment")
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(assignment.task_id)
        resource = self._resource_repo.get(assignment.resource_id)
        try:
            self._assignment_repo.delete(assignment_id)
            self._session.commit()
            if task is not None:
                record_assignment_action(
                    self,
                    action="assignment.remove",
                    assignment_id=assignment.id,
                    project_id=task.project_id,
                    task_name=task.name,
                    resource_name=resource.name if resource is not None else assignment.resource_id,
                )
        except Exception as exc:
            self._session.rollback()
            raise exc
        if task:
            domain_events.tasks_changed.emit(task.project_id)

    def list_assignments_for_task(self, task_id: str) -> List[TaskAssignment]:
        # Keep single-task queries aligned with primary repository API.
        return self._assignment_repo.list_by_task(task_id)

    def set_assignment_hours(self, assignment_id: str, hours_logged: float) -> TaskAssignment:
        self._require_manage("log assignment hours")
        if hours_logged < 0:
            raise ValidationError("hours_logged cannot be negative.")
        a = self._assignment_repo.get(assignment_id)
        if not a:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(a.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        a.hours_logged = hours_logged
        resource = self._resource_repo.get(a.resource_id)
        try:
            self._assignment_repo.update(a)
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.log_hours",
                assignment_id=a.id,
                project_id=task.project_id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else a.resource_id,
                extra={"hours_logged": a.hours_logged},
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        domain_events.tasks_changed.emit(task.project_id)
        return a

    def set_assignment_allocation(
        self,
        assignment_id: str,
        allocation_percent: float,
    ) -> TaskAssignment:
        self._require_manage("set assignment allocation")
        alloc = float(allocation_percent or 0.0)
        if alloc <= 0 or alloc > 100:
            raise ValidationError("allocation_percent must be > 0 and <= 100.")

        a = self._assignment_repo.get(assignment_id)
        if not a:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")

        task = self._task_repo.get(a.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        self._check_resource_overallocation(
            project_id=task.project_id,
            resource_id=a.resource_id,
            new_task_id=task.id,
            new_alloc_percent=alloc,
            exclude_assignment_id=a.id,
        )

        a.allocation_percent = alloc
        resource = self._resource_repo.get(a.resource_id)
        try:
            self._assignment_repo.update(a)
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.set_allocation",
                assignment_id=a.id,
                project_id=task.project_id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else a.resource_id,
                extra={"allocation_percent": a.allocation_percent},
            )
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
        self._require_manage("add assignment")
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
        resource = self._resource_repo.get(pr.resource_id)

        try:
            self._assignment_repo.add(assignment)
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.add",
                assignment_id=assignment.id,
                project_id=task.project_id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else pr.resource_id,
                extra={"allocation_percent": assignment.allocation_percent},
            )
        except Exception:
            self._session.rollback()
            raise

        domain_events.tasks_changed.emit(task.project_id)
        return assignment
