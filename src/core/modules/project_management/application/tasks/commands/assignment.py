from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common import (
    project_resource_envelope_policy as envelope_policy,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.resources.capacity.queries.availability import (
    ResourceAvailabilityQueryHandler,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.tasks.commands.assignment_activity import (
    record_assignment_action,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy_support import (
    TaskHierarchyPolicy,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
    TaskAssignmentPlannedHoursCommand,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskAssignmentChanged,
    TaskAssignmentChangeType,
)
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskResourceTimeBreakdownRow,
    TaskTimeSummaryFact,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.domain.tasks.task import TaskAssignment
from src.core.platform.application.security.authorization import (
    get_authorization_engine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    OperationNotPermittedError,
    ValidationError,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


@dataclass(frozen=True)
class TaskAssignmentActionContext:
    can_manage: bool
    can_accept: bool
    can_decline: bool


class TaskAssignmentCommandHandler(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        module_catalog_service=None,
        task_repo: TaskRepository,
        assignment_repo: AssignmentRepository,
        resource_repo: ResourceRepository,
        project_resource_repo: ProjectResourceRepository | None,
        time_entry_repo: TimeEntryRepository | None,
        employee_repo: EmployeeRepository | None,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService,
        hierarchy_policy: TaskHierarchyPolicy,
        validation_policy: TaskValidationPolicy,
        assignment_skill_validator: AssignmentSkillValidator | None,
        enterprise_resource_availability_service: ResourceAvailabilityQueryHandler | None,
        uow_scope: TaskUowScope,
        overallocation_policy: str,
    ) -> None:
        self._module_catalog_service = module_catalog_service
        self._task_repo = task_repo
        self._assignment_repo = assignment_repo
        self._resource_repo = resource_repo
        self._project_resource_repo = project_resource_repo
        self._time_entry_repo = time_entry_repo
        self._employee_repo = employee_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._hierarchy_policy = hierarchy_policy
        self._validation_policy = validation_policy
        self._assignment_skill_validator = assignment_skill_validator
        self._enterprise_resource_availability_service = enterprise_resource_availability_service
        self._uow_scope = uow_scope
        self._overallocation_policy = overallocation_policy
        self._last_overallocation_warning: str | None = None
        self._last_skill_violation_warning: str | None = None

    def _require_manage(self, operation_label: str, *, project_id: str | None = None) -> None:
        require_permission(self._user_session, "task.manage", operation_label=operation_label)
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "task.manage",
                operation_label=operation_label,
            )

    def _check_resource_overallocation(
        self,
        project_id: str,
        resource_id: str,
        new_task_id: str,
        new_alloc_percent: float,
        exclude_assignment_id: str | None = None,
    ) -> str | None:
        self._last_overallocation_warning = None
        warning = self._validation_policy.check_resource_overallocation(
            project_id,
            resource_id,
            new_task_id,
            new_alloc_percent,
            exclude_assignment_id,
            overallocation_policy=self._overallocation_policy,
        )
        self._last_overallocation_warning = warning
        return warning

    def consume_last_overallocation_warning(self) -> str | None:
        warning = self._last_overallocation_warning
        self._last_overallocation_warning = None
        return warning

    def consume_last_skill_violation_warning(self) -> str | None:
        warning = self._last_skill_violation_warning
        self._last_skill_violation_warning = None
        return warning

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
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="remove assignment"
        )
        with self._uow_scope.create() as uow:
            if uow.time_entries is not None:
                uow.time_entries.delete_by_assignment(assignment.id)
            uow.assignments.delete_with_version_check(
                assignment_id, expected_version=assignment.version
            )
            record_assignment_action(
                uow,
                action="assignment.remove",
                assignment_id=assignment.id,
                resource_id=assignment.resource_id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else assignment.resource_id,
                commit=False,
            )
            uow.record_event(
                TaskAssignmentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    assignment_id=assignment.id,
                    resource_id=assignment.resource_id,
                    change_type=TaskAssignmentChangeType.UNASSIGNED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()

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
        """Task-scoped (never resource-wide) planned/actual/remaining/overrun totals,
        plus the per-resource breakdown that explains them."""
        assignments = self.list_assignments_for_task(task_id)
        resources: list[Resource] = (
            self._resource_repo.list_by_ids(list({a.resource_id for a in assignments}))
            if assignments
            else []
        )
        resources_by_id = {resource.id: resource for resource in resources}

        rows: list[TaskResourceTimeBreakdownRow] = []
        planned_total = Decimal(0)
        actual_total = Decimal(0)
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
                    remaining_hours=max(planned - actual, Decimal(0)),
                    overrun_hours=max(actual - planned, Decimal(0)),
                    burn_status=envelope_policy.burn_status(
                        planned_hours=planned, actual_hours=actual
                    ),
                )
            )

        return TaskTimeSummaryFact(
            task_id=task_id,
            planned_hours=planned_total,
            actual_hours=actual_total,
            remaining_hours=max(planned_total - actual_total, Decimal(0)),
            overrun_hours=max(actual_total - planned_total, Decimal(0)),
            burn_status=envelope_policy.burn_status(
                planned_hours=planned_total, actual_hours=actual_total
            ),
            assignment_count=len(assignments),
            resource_breakdown=tuple(rows),
        )

    def set_assignment_hours(self, command: TaskAssignmentHoursCommand) -> TaskAssignment:
        assignment_id = command.assignment_id
        hours_logged = command.hours_logged
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        time_entry_repo = self._time_entry_repo
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
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="log assignment hours"
        )
        with self._uow_scope.create() as uow:
            updated = uow.assignments.update_hours_logged_with_version_check(
                candidate, expected_version=assignment.version
            )
            record_assignment_action(
                uow,
                action="assignment.log_hours",
                assignment_id=updated.id,
                resource_id=updated.resource_id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else updated.resource_id,
                extra={"hours_logged": updated.hours_logged},
                commit=False,
            )
            uow.record_event(
                TaskAssignmentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    assignment_id=updated.id,
                    resource_id=updated.resource_id,
                    change_type=TaskAssignmentChangeType.HOURS_CHANGED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()
        return updated

    def set_assignment_allocation(self, command: TaskAssignmentAllocationCommand) -> TaskAssignment:
        assignment_id = command.assignment_id
        allocation_percent = command.allocation_percent
        expected_version = command.expected_version
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
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="set assignment allocation"
        )
        with self._uow_scope.create() as uow:
            updated = uow.assignments.update_allocation_with_version_check(
                candidate, expected_version=expected_version
            )
            record_assignment_action(
                uow,
                action="assignment.set_allocation",
                assignment_id=updated.id,
                resource_id=updated.resource_id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else updated.resource_id,
                extra={"allocation_percent": updated.allocation_percent},
                commit=False,
            )
            uow.record_event(
                TaskAssignmentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    assignment_id=updated.id,
                    resource_id=updated.resource_id,
                    change_type=TaskAssignmentChangeType.ALLOCATION_CHANGED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()

        return updated

    def update_assignment_planned_hours(self, command: TaskAssignmentPlannedHoursCommand) -> TaskAssignment:
        assignment_id = command.assignment_id
        allocated_planned_hours = command.allocated_planned_hours
        expected_assignment_version = command.expected_assignment_version
        expected_project_resource_version = command.expected_project_resource_version
        """Distributes a ProjectResource.planned_hours envelope across task assignments."""
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
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="update assignment planned hours"
        )
        with self._uow_scope.create() as uow:
            updated = uow.assignments.update_planned_hours_with_version_check(
                candidate, expected_version=expected_assignment_version
            )
            self._project_resource_repo.touch_version_with_check(
                project_resource.id,
                expected_version=expected_project_resource_version,
            )
            record_assignment_action(
                uow,
                action="assignment.update_planned_hours",
                assignment_id=updated.id,
                resource_id=updated.resource_id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else updated.resource_id,
                extra={
                    "allocated_planned_hours": str(updated.allocated_planned_hours),
                    "project_resource_planned_hours": str(project_resource.planned_hours),
                    "allocated_total": str(proposed_total),
                },
                commit=False,
            )
            uow.record_event(
                TaskAssignmentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    assignment_id=updated.id,
                    resource_id=updated.resource_id,
                    change_type=TaskAssignmentChangeType.PLANNED_HOURS_CHANGED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()
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

    def assign_resource(
        self, task_id: str, resource_id: str, allocation_percent: float = 100.0
    ) -> TaskAssignment:
        """Auto-provision the ProjectResource envelope, then use the canonical assignment path."""
        self._require_manage("add assignment")
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("add assignment", project_id=task.project_id)
        self._hierarchy_policy._require_leaf_task(
            task, operation_label="receive resource assignments"
        )
        if self._project_resource_repo is None:
            raise BusinessRuleError(
                "Project resource repository is not configured.",
                code="PROJECT_RESOURCE_REPO_MISSING",
            )
        resource = self._resource_repo.get(resource_id)
        if resource is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        assignment = TaskAssignment.create(task_id, resource_id, allocation_percent)

        with self._uow_scope.create() as uow:
            project_resource = uow.project_resources.get_for_project(task.project_id, resource_id)
            if project_resource is None:
                project_resource = ProjectResource.create(
                    project_id=task.project_id,
                    resource_id=resource_id,
                    hourly_rate=getattr(resource, "hourly_rate", None),
                    currency_code=getattr(resource, "currency_code", None),
                    planned_hours=Decimal(0),
                    is_active=bool(getattr(resource, "is_active", True)),
                )
                uow.project_resources.add(project_resource)

            return self._assign_project_resource_in_uow(
                task_id=task_id,
                project_resource_id=project_resource.id,
                allocation_percent=assignment.allocation_percent,
                allocated_planned_hours=Decimal(0),
                uow=uow,
                project_resource=project_resource,
            )

    def assign_project_resource(self, command: TaskAssignmentCreateCommand) -> TaskAssignment:
        task_id = command.task_id
        project_resource_id = command.project_resource_id
        allocation_percent = command.allocation_percent
        allocated_planned_hours = command.allocated_planned_hours
        with self._uow_scope.create() as uow:
            project_resource = uow.project_resources.get(project_resource_id)
            if not project_resource:
                raise NotFoundError(
                    "Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND"
                )
            return self._assign_project_resource_in_uow(
                task_id=task_id,
                project_resource_id=project_resource_id,
                allocation_percent=allocation_percent,
                allocated_planned_hours=allocated_planned_hours,
                project_resource=project_resource,
                uow=uow,
            )

    def _assign_project_resource_in_uow(
        self,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
        *,
        allocated_planned_hours: Decimal,
        project_resource: ProjectResource,
        uow,
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
        self._hierarchy_policy._require_leaf_task(
            task, operation_label="receive resource assignments"
        )

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
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="add assignment"
        )

        with nullcontext(uow):
            uow.assignments.add(assignment)
            record_assignment_action(
                uow,
                action="assignment.add",
                assignment_id=assignment.id,
                resource_id=assignment.resource_id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else project_resource.resource_id,
                extra={
                    "allocation_percent": assignment.allocation_percent,
                    "allocated_planned_hours": str(assignment.allocated_planned_hours),
                },
                commit=False,
            )
            uow.record_event(
                TaskAssignmentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    assignment_id=assignment.id,
                    resource_id=assignment.resource_id,
                    change_type=TaskAssignmentChangeType.ASSIGNED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()

        return assignment

    def _check_resource_skill_requirements(self, *, task, resource_id: str) -> None:
        self._last_skill_violation_warning = None
        validator = self._assignment_skill_validator
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
        employee_repo = self._employee_repo
        employee = None
        employee_id = getattr(resource, "employee_id", None) if resource is not None else None
        if employee_repo is not None and employee_id:
            employee = employee_repo.get(employee_id)
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
        """Read-only capacity preview using the same authority
        `_check_resource_overallocation` uses at save time, so preview and
        enforcement cannot disagree. Advisory only -- never raises on
        over-capacity, and always re-evaluated fresh."""
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
        availability_service = self._enterprise_resource_availability_service
        if availability_service is None:
            return None
        task_start = getattr(task, "start_date", None)
        task_end = getattr(task, "end_date", None)
        if not task_start or not task_end:
            return None
        from src.core.modules.project_management.application.resources.capacity.task_assignment_capacity_service import (
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
        employee_repo = self._employee_repo
        employee = None
        employee_id = getattr(resource, "employee_id", None) if resource is not None else None
        if employee_repo is not None and employee_id:
            employee = employee_repo.get(employee_id)
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
            responded_at=datetime.now(UTC),
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="accept assignment"
        )
        with self._uow_scope.create() as uow:
            updated = uow.assignments.update_response_status_with_version_check(
                candidate, expected_version=assignment.version
            )
            record_assignment_action(
                uow,
                action="assignment.accept",
                assignment_id=updated.id,
                resource_id=updated.resource_id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else updated.resource_id,
                commit=False,
            )
            uow.record_event(
                TaskAssignmentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    assignment_id=updated.id,
                    resource_id=updated.resource_id,
                    change_type=TaskAssignmentChangeType.ACCEPTED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()
        return updated

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
            responded_at=datetime.now(UTC),
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="decline assignment"
        )
        with self._uow_scope.create() as uow:
            updated = uow.assignments.update_response_status_with_version_check(
                candidate, expected_version=assignment.version
            )
            record_assignment_action(
                uow,
                action="assignment.decline",
                assignment_id=updated.id,
                resource_id=updated.resource_id,
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                resource_name=resource.name if resource is not None else updated.resource_id,
                extra={"reason": reason} if reason else None,
                commit=False,
            )
            uow.record_event(
                TaskAssignmentChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    assignment_id=updated.id,
                    resource_id=updated.resource_id,
                    change_type=TaskAssignmentChangeType.DECLINED,
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()
        return updated


__all__ = ["TaskAssignmentActionContext", "TaskAssignmentCommandHandler"]
