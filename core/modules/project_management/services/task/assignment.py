from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.modules.project_management.contracts.repositories.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.domain.tasks.task import TaskAssignment
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from core.modules.project_management.services.task.assignment_audit import record_assignment_action


class TaskAssignmentMixin:
    _session: Session
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _project_resource_repo: ProjectResourceRepository | None

    def _require_manage(self, operation_label: str, *, project_id: str | None = None) -> None:
        require_permission(self._user_session, "task.manage", operation_label=operation_label)
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "task.manage",
                operation_label=operation_label,
            )

    def unassign_resource(self, assignment_id: str) -> None:
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(assignment.task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("remove assignment", project_id=task.project_id)
        resource = self._resource_repo.get(assignment.resource_id)
        try:
            time_entry_repo = getattr(self, "_time_entry_repo", None)
            if time_entry_repo is not None:
                time_entry_repo.delete_by_assignment(assignment.id)
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
        require_permission(self._user_session, "task.read", operation_label="list task assignments")
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="list task assignments",
        )
        # Keep single-task queries aligned with primary repository API.
        return self._assignment_repo.list_by_task(task_id)

    def set_assignment_hours(self, assignment_id: str, hours_logged: float) -> TaskAssignment:
        if hours_logged < 0:
            raise ValidationError("hours_logged cannot be negative.")
        a = self._assignment_repo.get(assignment_id)
        if not a:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        time_entry_repo = getattr(self, "_time_entry_repo", None)
        if time_entry_repo is not None and time_entry_repo.list_by_assignment(assignment_id):
            raise ValidationError(
                "This assignment already uses timesheet entries. Edit the timesheet instead of the aggregate hours."
            )
        task = self._task_repo.get(a.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("log assignment hours", project_id=task.project_id)
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
        alloc = float(allocation_percent or 0.0)
        if alloc <= 0 or alloc > 100:
            raise ValidationError("allocation_percent must be > 0 and <= 100.")

        a = self._assignment_repo.get(assignment_id)
        if not a:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")

        task = self._task_repo.get(a.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("set assignment allocation", project_id=task.project_id)

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
        require_permission(self._user_session, "task.read", operation_label="view assignment")
        assignment = self._assignment_repo.get(assignment_id)
        if assignment is None:
            return None
        task = self._task_repo.get(assignment.task_id)
        if task is None:
            return None
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="view assignment",
        )
        return assignment

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
        self._require_manage("add assignment", project_id=task.project_id)

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
