from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.tasks.commands.assignment_activity import (
    record_assignment_action,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import TaskAssignment
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.application.security.authorization import get_authorization_engine
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    OperationNotPermittedError,
    ValidationError,
)
from src.core.shared.events.domain_events import domain_events
from src.core.shared.notifications import safe_dispatch_notification


@dataclass(frozen=True)
class TaskAssignmentActionContext:
    can_manage: bool
    can_accept: bool
    can_decline: bool


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
            record_assignment_action(
                self,
                action="assignment.remove",
                assignment_id=assignment.id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else assignment.resource_id,
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        domain_events.tasks_changed.emit(task.project_id)

    def list_assignments_for_task(self, task_id: str) -> list[TaskAssignment]:
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
        return self._assignment_repo.list_by_task(task_id)

    def set_assignment_hours(self, assignment_id: str, hours_logged: float) -> TaskAssignment:
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        time_entry_repo = getattr(self, "_time_entry_repo", None)
        if time_entry_repo is not None and time_entry_repo.list_by_assignment(assignment_id):
            raise ValidationError(
                "This assignment already uses timesheet entries. Edit the timesheet instead of the aggregate hours."
            )
        task = self._task_repo.get(assignment.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("log assignment hours", project_id=task.project_id)
        candidate = replace(assignment, hours_logged=hours_logged)
        resource = self._resource_repo.get(assignment.resource_id)
        try:
            self._assignment_repo.update(candidate)
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.log_hours",
                assignment_id=candidate.id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else candidate.resource_id,
                extra={"hours_logged": candidate.hours_logged},
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        domain_events.tasks_changed.emit(task.project_id)
        return candidate

    def set_assignment_allocation(
        self,
        assignment_id: str,
        allocation_percent: float,
    ) -> TaskAssignment:
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")

        task = self._task_repo.get(assignment.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("set assignment allocation", project_id=task.project_id)
        candidate = replace(assignment, allocation_percent=allocation_percent)

        self._check_resource_overallocation(
            project_id=task.project_id,
            resource_id=assignment.resource_id,
            new_task_id=task.id,
            new_alloc_percent=candidate.allocation_percent,
            exclude_assignment_id=assignment.id,
        )

        resource = self._resource_repo.get(assignment.resource_id)
        try:
            self._assignment_repo.update(candidate)
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.set_allocation",
                assignment_id=candidate.id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else candidate.resource_id,
                extra={"allocation_percent": candidate.allocation_percent},
            )
        except Exception as exc:
            self._session.rollback()
            raise exc

        domain_events.tasks_changed.emit(task.project_id)
        return candidate

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

        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("add assignment", project_id=task.project_id)
        self._require_leaf_task(task, operation_label="receive resource assignments")

        project_resource = self._project_resource_repo.get(project_resource_id)
        if not project_resource:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")

        if project_resource.project_id != task.project_id:
            raise BusinessRuleError(
                "Selected resource is not linked to this task's project.",
                code="PROJECT_RESOURCE_MISMATCH",
            )

        if not getattr(project_resource, "is_active", True):
            raise BusinessRuleError("This project resource is inactive.", code="PROJECT_RESOURCE_INACTIVE")

        existing = self._assignment_repo.list_by_task(task_id)
        if any(a.resource_id == project_resource.resource_id for a in existing):
            raise ValidationError(
                "Resource is already assigned to this task.",
                code="ASSIGNMENT_DUPLICATE",
            )

        assignment = TaskAssignment.create(
            task_id,
            project_resource.resource_id,
            allocation_percent,
        )
        assignment.project_resource_id = project_resource.id

        self._check_resource_overallocation(
            project_id=task.project_id,
            resource_id=project_resource.resource_id,
            new_task_id=task.id,
            new_alloc_percent=assignment.allocation_percent,
        )
        self._check_resource_skill_requirements(task=task, resource_id=project_resource.resource_id)
        resource = self._resource_repo.get(project_resource.resource_id)

        try:
            self._assignment_repo.add(assignment)
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.add",
                assignment_id=assignment.id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else project_resource.resource_id,
                extra={"allocation_percent": assignment.allocation_percent},
            )
        except Exception:
            self._session.rollback()
            raise

        domain_events.tasks_changed.emit(task.project_id)
        self._notify_task_assigned(task=task, resource=resource)
        return assignment

    def _check_resource_skill_requirements(self, *, task, resource_id: str) -> None:
        self._last_skill_violation_warning = None
        validator = getattr(self, "_assignment_skill_validator", None)
        if validator is None:
            return
        result = validator.validate(task, resource_id)
        if result.is_blocked:
            blocking = result.violations[0].message if result.violations else "Resource does not meet the required skills/certifications for this task."
            raise BusinessRuleError(blocking, code="ASSIGNMENT_SKILL_BLOCKED")
        if result.warnings or result.requires_approval:
            messages = [violation.message for violation in (*result.violations, *result.warnings)]
            self._last_skill_violation_warning = "\n".join(messages)

    def _resolve_assignment_for_response(self, assignment_id: str):
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(assignment.task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_permission(self._user_session, "task.read", operation_label="respond to task assignment")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="respond to task assignment",
        )
        resource = self._resource_repo.get(assignment.resource_id)
        employee_repo = getattr(self, "_employee_repo", None)
        employee = None
        if resource is not None and employee_repo is not None and getattr(resource, "employee_id", None):
            employee = employee_repo.get(resource.employee_id)
        assignee_user_id = getattr(employee, "user_id", None) if employee is not None else None
        if not assignee_user_id:
            raise BusinessRuleError(
                "This assignment has no linked user account to respond on its behalf.",
                code="ASSIGNMENT_NO_LINKED_USER",
            )
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not principal_user_id or principal_user_id != assignee_user_id:
            raise OperationNotPermittedError(
                "Only the assigned resource's own user account can respond to this assignment.",
                code="ASSIGNMENT_NOT_ASSIGNEE",
            )
        return assignment, task, resource

    def get_assignment_action_context(
        self,
        assignment_id: str,
    ) -> TaskAssignmentActionContext:
        """Return fail-closed assignment capabilities for desktop presentation."""
        assignment = self._assignment_repo.get(assignment_id)
        if assignment is None:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(assignment.task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        engine = get_authorization_engine()
        can_read = engine.has_permission(
            self._user_session,
            "task.read",
        ) and engine.has_scope_permission(
            self._user_session,
            "project",
            task.project_id,
            "task.read",
        )
        can_manage = engine.has_permission(
            self._user_session,
            "task.manage",
        ) and engine.has_scope_permission(
            self._user_session,
            "project",
            task.project_id,
            "task.manage",
        )

        principal = (
            self._user_session.principal
            if self._user_session is not None
            else None
        )
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        resource = self._resource_repo.get(assignment.resource_id)
        employee_repo = getattr(self, "_employee_repo", None)
        employee = None
        if (
            resource is not None
            and employee_repo is not None
            and getattr(resource, "employee_id", None)
        ):
            employee = employee_repo.get(resource.employee_id)
        assignee_user_id = str(getattr(employee, "user_id", "") or "").strip()
        can_respond = bool(
            can_read
            and principal_user_id
            and principal_user_id == assignee_user_id
            and assignment.response_status == "pending"
        )
        return TaskAssignmentActionContext(
            can_manage=bool(can_manage),
            can_accept=can_respond,
            can_decline=can_respond,
        )

    def accept_assignment(self, assignment_id: str) -> TaskAssignment:
        assignment, task, resource = self._resolve_assignment_for_response(assignment_id)
        if assignment.response_status == "accepted":
            return assignment
        if assignment.response_status != "pending":
            raise BusinessRuleError(
                "This assignment has already been declined and must be reassigned before it can be accepted.",
                code="ASSIGNMENT_ALREADY_RESPONDED",
            )
        candidate = replace(
            assignment,
            response_status="accepted",
            responded_at=datetime.now(timezone.utc),
        )
        try:
            self._assignment_repo.update(candidate)
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.accept",
                assignment_id=candidate.id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else candidate.resource_id,
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.tasks_changed.emit(task.project_id)
        return candidate

    def decline_assignment(
        self,
        assignment_id: str,
        reason: str | None = None,
    ) -> TaskAssignment:
        assignment, task, resource = self._resolve_assignment_for_response(assignment_id)
        if assignment.response_status == "declined":
            return assignment
        if assignment.response_status != "pending":
            raise BusinessRuleError(
                "This assignment has already been accepted and must be reassigned before it can be declined.",
                code="ASSIGNMENT_ALREADY_RESPONDED",
            )
        candidate = replace(
            assignment,
            response_status="declined",
            responded_at=datetime.now(timezone.utc),
        )
        try:
            self._assignment_repo.update(candidate)
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.decline",
                assignment_id=candidate.id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else candidate.resource_id,
                extra={"reason": reason} if reason else None,
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.tasks_changed.emit(task.project_id)
        return candidate

    def _notify_task_assigned(self, *, task, resource) -> None:
        if resource is None or not getattr(resource, "employee_id", None):
            return
        employee_repo = getattr(self, "_employee_repo", None)
        if employee_repo is None:
            return
        employee = employee_repo.get(resource.employee_id)
        if employee is None or not getattr(employee, "user_id", None):
            return
        task_name = getattr(task, "name", "") or task.id
        safe_dispatch_notification(
            self,
            recipient_user_id=employee.user_id,
            category="pm.task.assigned.v1",
            title="You were assigned a task",
            body=f'You were assigned to "{task_name}".',
            metadata={"task_id": task.id, "project_id": task.project_id},
        )


__all__ = ["TaskAssignmentActionContext", "TaskAssignmentMixin"]
