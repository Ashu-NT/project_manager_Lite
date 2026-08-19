from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common import (
    project_resource_envelope_policy as envelope_policy,
)
from src.core.modules.project_management.application.tasks.commands.assignment_activity import (
    record_assignment_action,
)
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskResourceTimeBreakdownRow,
    TaskTimeSummaryFact,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import (
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
        # Historical actual work must not disappear because a planning
        # assignment is removed -- once real hours are logged, removing the
        # assignment would otherwise silently delete that labor history too.
        if assignment.hours_logged and assignment.hours_logged > 0:
            raise BusinessRuleError(
                "This assignment has recorded actual time. Remove the resource "
                "from future planning by declining/reassigning instead of "
                "deleting the assignment, to preserve the historical record.",
                code="ASSIGNMENT_HAS_HISTORICAL_ACTUALS",
            )
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

    def get_task_time_summary(self, task_id: str) -> TaskTimeSummaryFact:
        """Task-scoped (never resource-wide) planned/actual/remaining/
        overrun totals for Task Detail -> Time -> Overview (docs §44 Time
        redesign), plus the per-resource breakdown that explains them.
        Reuses the existing envelope_policy.burn_status authority -- one
        vocabulary for "how does actual compare to plan" across
        ProjectResource and Task scopes."""
        assignments = self.list_assignments_for_task(task_id)
        resources_by_id = {
            r.id: r
            for r in self._resource_repo.list_by_ids(
                list({a.resource_id for a in assignments})
            )
        } if assignments else {}

        rows: list[TaskResourceTimeBreakdownRow] = []
        planned_total = Decimal("0")
        actual_total = Decimal("0")
        for assignment in assignments:
            planned = Decimal(str(assignment.allocated_planned_hours or 0))
            actual = Decimal(str(assignment.hours_logged or 0))
            planned_total += planned
            actual_total += actual
            resource = resources_by_id.get(assignment.resource_id)
            rows.append(
                TaskResourceTimeBreakdownRow(
                    assignment_id=assignment.id,
                    resource_id=assignment.resource_id,
                    resource_name=getattr(resource, "name", "") or assignment.resource_id,
                    planned_hours=planned,
                    actual_hours=actual,
                    remaining_hours=max(planned - actual, Decimal("0")),
                    overrun_hours=max(actual - planned, Decimal("0")),
                    burn_status=envelope_policy.burn_status(
                        planned_hours=planned, actual_hours=actual
                    ),
                )
            )

        return TaskTimeSummaryFact(
            task_id=task_id,
            planned_hours=planned_total,
            actual_hours=actual_total,
            remaining_hours=max(planned_total - actual_total, Decimal("0")),
            overrun_hours=max(actual_total - planned_total, Decimal("0")),
            burn_status=envelope_policy.burn_status(
                planned_hours=planned_total, actual_hours=actual_total
            ),
            assignment_count=len(assignments),
            resource_breakdown=tuple(rows),
        )

    def set_assignment_hours(self, assignment_id: str, hours_logged: Decimal) -> TaskAssignment:
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
        *,
        expected_version: int | None = None,
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
            if expected_version is not None:
                updated = self._assignment_repo.update_allocation_with_version_check(
                    candidate, expected_version=expected_version
                )
            else:
                self._assignment_repo.update(candidate)
                updated = candidate
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.set_allocation",
                assignment_id=updated.id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else updated.resource_id,
                extra={"allocation_percent": updated.allocation_percent},
            )
        except Exception as exc:
            self._session.rollback()
            raise exc

        domain_events.tasks_changed.emit(task.project_id)
        return updated

    def update_assignment_planned_hours(
        self,
        assignment_id: str,
        *,
        allocated_planned_hours: Decimal,
        expected_assignment_version: int,
        expected_project_resource_version: int,
    ) -> TaskAssignment:
        """Tactical WBS distribution of a ``ProjectResource.planned_hours envelope """
        if not self._project_resource_repo:
            raise BusinessRuleError(
                "Project resource repository is not configured.",
                code="PROJECT_RESOURCE_REPO_MISSING",
            )
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(assignment.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("update assignment planned hours", project_id=task.project_id)

        project_resource = (
            self._project_resource_repo.get(assignment.project_resource_id)
            if assignment.project_resource_id
            else self._project_resource_repo.get_for_project(task.project_id, assignment.resource_id)
        )
        if project_resource is None:
            raise BusinessRuleError(
                "This resource has no project-resource planning envelope for this project.",
                code="PROJECT_RESOURCE_ENVELOPE_MISSING",
            )
        if (
            project_resource.project_id != task.project_id
            or project_resource.resource_id != assignment.resource_id
        ):
            raise BusinessRuleError(
                "Project resource does not match this assignment's task/resource.",
                code="PROJECT_RESOURCE_MISMATCH",
            )

        proposed_hours, proposed_total = self._check_planned_hours_envelope(
            project_resource=project_resource,
            resource_id=assignment.resource_id,
            allocated_planned_hours=allocated_planned_hours,
            exclude_assignment_id=assignment.id,
        )

        candidate = replace(assignment, allocated_planned_hours=proposed_hours)
        resource = self._resource_repo.get(assignment.resource_id)
        try:
            updated = self._assignment_repo.update_planned_hours_with_version_check(
                candidate, expected_version=expected_assignment_version
            )
            self._project_resource_repo.touch_version_with_check(
                project_resource.id,
                expected_version=expected_project_resource_version,
            )
            self._session.commit()
            record_assignment_action(
                self,
                action="assignment.update_planned_hours",
                assignment_id=updated.id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else updated.resource_id,
                extra={
                    "allocated_planned_hours": str(updated.allocated_planned_hours),
                    "project_resource_planned_hours": str(project_resource.planned_hours),
                    "allocated_total": str(proposed_total),
                },
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.tasks_changed.emit(task.project_id)
        return updated

    def _check_planned_hours_envelope(
        self,
        *,
        project_resource,
        resource_id: str,
        allocated_planned_hours: Decimal,
        exclude_assignment_id: str | None = None,
    ) -> tuple[Decimal, Decimal]:
        """Validate a proposed ``allocated_planned_hours`` value against the
        resource's shared ``ProjectResource.planned_hours`` envelope for this
        project, via the single shared envelope policy. Returns
        ``(proposed_hours, proposed_total)`` on success."""
        other_total = envelope_policy.allocated_to_tasks_hours(
            task_repo=self._task_repo,
            assignment_repo=self._assignment_repo,
            project_id=project_resource.project_id,
            resource_id=resource_id,
            exclude_assignment_id=exclude_assignment_id,
        )
        proposed_hours = Decimal(str(allocated_planned_hours))
        envelope_hours = Decimal(str(project_resource.planned_hours))
        proposed_total = envelope_policy.require_can_allocate_task_hours(
            planned_hours=envelope_hours,
            allocated_total_excluding_this_task=other_total,
            proposed_task_hours=proposed_hours,
            resource_id=resource_id,
        )
        return proposed_hours, proposed_total

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
        self,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
        *,
        allocated_planned_hours: Decimal = Decimal("0"),
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

        resource_for_check = self._resource_repo.get(project_resource.resource_id)
        if resource_for_check is not None and not getattr(resource_for_check, "is_active", True):
            raise BusinessRuleError(
                "This resource is inactive and cannot be assigned to tasks.",
                code="RESOURCE_INACTIVE",
            )

        existing = self._assignment_repo.list_by_task(task_id)
        if any(a.resource_id == project_resource.resource_id for a in existing):
            raise ValidationError(
                "Resource is already assigned to this task.",
                code="ASSIGNMENT_DUPLICATE",
            )

        proposed_planned_hours = Decimal(str(allocated_planned_hours or 0))
        if proposed_planned_hours > 0:
            proposed_planned_hours, _ = self._check_planned_hours_envelope(
                project_resource=project_resource,
                resource_id=project_resource.resource_id,
                allocated_planned_hours=proposed_planned_hours,
            )

        assignment = TaskAssignment.create(
            task_id,
            project_resource.resource_id,
            allocation_percent,
            allocated_planned_hours=proposed_planned_hours,
        )
        assignment.project_resource_id = project_resource.id

        self._check_resource_overallocation(
            project_id=task.project_id,
            resource_id=project_resource.resource_id,
            new_task_id=task.id,
            new_alloc_percent=assignment.allocation_percent,
        )
        self._check_resource_skill_requirements(task=task, resource_id=project_resource.resource_id)
        resource = resource_for_check

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
                extra={
                    "allocation_percent": assignment.allocation_percent,
                    "allocated_planned_hours": str(assignment.allocated_planned_hours),
                },
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

    def preview_assignment_capacity(
        self,
        task_id: str,
        resource_id: str,
        *,
        proposed_allocation_percent: float = 100.0,
        exclude_assignment_id: str | None = None,
    ):
        """Read-only authoritative capacity preview (docs §44) -- calls the
        exact same `evaluate_task_assignment_capacity` authority
        `_check_resource_overallocation` uses at save time, so preview and
        enforcement cannot disagree by construction (there is only one
        implementation). This is advisory only: it does not raise on
        over-capacity (that is enforcement's job at save time, gated by the
        warn/strict policy) and is always re-evaluated fresh -- nothing
        about a preview computed moments earlier is trusted as final."""
        require_permission(self._user_session, "task.read", operation_label="preview assignment capacity")
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="preview assignment capacity",
        )
        availability_service = getattr(self, "_enterprise_resource_availability_service", None)
        if availability_service is None:
            return None
        task_start = getattr(task, "start_date", None)
        task_end = getattr(task, "end_date", None)
        if not task_start or not task_end:
            return None
        from src.core.modules.project_management.application.resources.task_assignment_capacity_service import (
            evaluate_task_assignment_capacity,
        )

        return evaluate_task_assignment_capacity(
            resource_id=resource_id,
            project_id=task.project_id,
            start_date=task_start,
            end_date=task_end,
            proposed_allocation_percent=proposed_allocation_percent,
            task_repo=self._task_repo,
            assignment_repo=self._assignment_repo,
            resource_repo=self._resource_repo,
            availability_service=availability_service,
            exclude_assignment_id=exclude_assignment_id,
        )

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
