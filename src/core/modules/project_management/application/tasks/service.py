from __future__ import annotations

import os
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks.commands.approved_schedule_change import (
    ApprovedScheduleChangeMixin,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentMixin,
)
from src.core.modules.project_management.application.tasks.commands.assignment_bridge import (
    TaskAssignmentBridgeMixin,
)
from src.core.modules.project_management.application.tasks.commands.deletion import (
    TaskDeletionMixin,
)
from src.core.modules.project_management.application.tasks.commands.dependency import (
    TaskDependencyMixin,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy import (
    TaskHierarchyMixin,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy_support import (
    TaskHierarchySupportMixin,
)
from src.core.modules.project_management.application.tasks.commands.identity import (
    TaskCodePolicy,
)
from src.core.modules.project_management.application.tasks.commands.lifecycle import (
    TaskLifecycleMixin,
)
from src.core.modules.project_management.application.tasks.commands.progress import (
    TaskProgressMixin,
)
from src.core.modules.project_management.application.tasks.commands.resource_leveling_apply import (
    ResourceLevelingApplyMixin,
)
from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSynchronizer,
)
from src.core.modules.project_management.application.tasks.commands.scheduling_constraint import (
    TaskSchedulingConstraintMixin,
)
from src.core.modules.project_management.application.tasks.commands.time_entries import (
    TaskTimeEntryMixin,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    DependencyDiagnostic,
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.hierarchy_query import (
    TaskHierarchyQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_workspace_page import (
    TaskWorkspacePageQueryHandler,
)
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskActivityPage,
    TaskAssignmentReadPage,
    TaskDependencyReadPage,
    TaskWorkspaceReader,
    TaskWorkspaceReadPage,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
    TimesheetAssignmentContext,
)
from src.core.modules.project_management.contracts.uow.tasks.task_unit_of_work import (
    TaskUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.modules.project_management.domain.tasks.hierarchy import (
    TaskHierarchyNode,
    TaskHierarchyRollup,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
    TimesheetPeriodRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.events.domain_event_context import DomainEventContext


class TaskService(
    ProjectManagementModuleGuardMixin,
    ApprovedScheduleChangeMixin,
    TaskHierarchySupportMixin,
    TaskHierarchyMixin,
    TaskProgressMixin,
    TaskDeletionMixin,
    TaskLifecycleMixin,
    TaskDependencyMixin,
    TaskSchedulingConstraintMixin,
    ResourceLevelingApplyMixin,
    TaskAssignmentMixin,
    TaskTimeEntryMixin,
    TaskAssignmentBridgeMixin,
):
    """Task application service orchestrator."""

    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        time_entry_repo: TimeEntryRepository | None,
        timesheet_period_repo: TimesheetPeriodRepository | None,
        timesheet_service: TimesheetService | None,
        resource_repo: ResourceRepository,
        work_calendar_engine: CalendarProtocol,
        scheduling_engine: SchedulingEngine | None = None,
        project_resource_repo: ProjectResourceRepository | None = None,
        project_repo: ProjectRepository | None = None,
        user_session: UserSessionContext | None = None,
        activity_service: ActivityService | None = None,
        approval_service: ApprovalService | None = None,
        module_catalog_service=None,
        employee_repo=None,
        assignment_skill_validator=None,
        tenant_context_service=None,
        task_workspace_reader: TaskWorkspaceReader | None = None,
        enterprise_resource_availability_service=None,
        task_uow_factory: TaskUnitOfWorkFactory | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
        *,
        detail_query_handler: TaskDetailPageQueryHandler,
        workspace_query_handler: TaskWorkspacePageQueryHandler,
        lookup_query_handler: TaskLookupQueryHandler,
        hierarchy_query_handler: TaskHierarchyQueryHandler,
        dependency_diagnostics_handler: TaskDependencyDiagnosticsQueryHandler,
        code_policy: TaskCodePolicy,
        validation_policy: TaskValidationPolicy,
        schedule_synchronizer: TaskScheduleSynchronizer,
    ):
        self._session: Session = session
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._time_entry_repo = time_entry_repo
        self._timesheet_period_repo = timesheet_period_repo
        self._timesheet_service = timesheet_service
        self._resource_repo: ResourceRepository = resource_repo
        self._work_calendar_engine: CalendarProtocol = work_calendar_engine
        self._scheduling_engine: SchedulingEngine | None = scheduling_engine
        self._project_resource_repo: ProjectResourceRepository | None = project_resource_repo
        self._project_repo: ProjectRepository | None = project_repo
        self._user_session: UserSessionContext | None = user_session
        self._activity_service: ActivityService | None = activity_service
        self._approval_service: ApprovalService | None = approval_service
        self._module_catalog_service = module_catalog_service
        self._employee_repo = employee_repo
        self._assignment_skill_validator = assignment_skill_validator
        self._tenant_context_service = tenant_context_service
        self._task_workspace_reader = task_workspace_reader
        self._detail_query = detail_query_handler
        self._workspace_query = workspace_query_handler
        self._lookup_query = lookup_query_handler
        self._hierarchy_query = hierarchy_query_handler
        self._dependency_diagnostics = dependency_diagnostics_handler
        self._code_policy = code_policy
        self._validation_policy = validation_policy
        self._schedule_synchronizer = schedule_synchronizer
        self._enterprise_resource_availability_service = enterprise_resource_availability_service
        policy = os.getenv("PM_OVERALLOCATION_POLICY", "warn").strip().lower()
        self._overallocation_policy: str = "strict" if policy == "strict" else "warn"
        self._last_overallocation_warning: str | None = None
        self._last_skill_violation_warning: str | None = None
        self._task_uow_factory: TaskUnitOfWorkFactory | None = task_uow_factory
        self._enterprise_audit_service: EnterpriseAuditService | None = enterprise_audit_service
        # Sidecar for the passthrough (approval/cross-capability) UoW mode: the
        # caller (e.g. task_apply_participant) owns commit/dispatch and must
        # collect the typed fact(s) a mutation recorded via this list right
        # after calling it -- see `application/tasks/task_unit_of_work_scope.py`.
        self._pending_task_events: list = []

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def _resolve_task_code(
        self, code: str, project_id: str, name: str, *, exclude_id: str | None = None
    ) -> str:
        return self._code_policy.resolve_task_code(
            code, project_id, name, exclude_id=exclude_id
        )

    def _is_task_code_integrity_error(self, exc: IntegrityError) -> bool:
        return self._code_policy.is_task_code_integrity_error(exc)

    def _raise_task_code_duplicate(self, code: str, exc: IntegrityError) -> None:
        self._code_policy.raise_task_code_duplicate(code, exc)

    def _validate_task_within_project_dates(
        self, project_id: str, task_start: date | None, task_end: date | None
    ) -> None:
        self._validation_policy.validate_task_within_project_dates(
            project_id, task_start, task_end
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

    def _sync_project_schedule(
        self,
        project_id: str | None,
        *,
        commit: bool,
        exclude_task_ids: frozenset[str] = frozenset(),
    ) -> list[str]:
        return self._schedule_synchronizer.sync_project_schedule(
            project_id, commit=commit, exclude_task_ids=exclude_task_ids
        )

    def get_task(self, task_id: str) -> Task | None:
        return self._detail_query.get_task(task_id)

    def list_task_hierarchy(self, project_id: str) -> list[TaskHierarchyNode]:
        return self._hierarchy_query.list_task_hierarchy(project_id)

    def list_leaf_tasks_for_project(self, project_id: str) -> list[Task]:
        return self._hierarchy_query.list_leaf_tasks_for_project(project_id)

    def get_task_hierarchy_rollup(self, task_id: str) -> TaskHierarchyRollup:
        return self._hierarchy_query.get_task_hierarchy_rollup(task_id)

    def list_task_hierarchy_rollups(
        self, project_id: str
    ) -> dict[str, TaskHierarchyRollup]:
        return self._hierarchy_query.list_task_hierarchy_rollups(project_id)

    def get_dependency_diagnostics(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
        include_impact: bool = True,
        exclude_dependency_id: str | None = None,
    ) -> DependencyDiagnostic:
        return self._dependency_diagnostics.get_dependency_diagnostics(
            predecessor_id,
            successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            include_impact=include_impact,
            exclude_dependency_id=exclude_dependency_id,
        )

    def preview_dependency_removal(self, dependency_id: str) -> DependencyDiagnostic:
        return self._dependency_diagnostics.preview_dependency_removal(dependency_id)

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return self._lookup_query.list_tasks_for_project(project_id)

    def list_tasks_for_resource(self, resource_id: str) -> list[Task]:
        return self._lookup_query.list_tasks_for_resource(resource_id)

    def list_assignments_for_resource(self, resource_id: str) -> list[TaskAssignment]:
        return self._lookup_query.list_assignments_for_resource(resource_id)

    def list_assignments_for_tasks(self, task_ids: list[str]) -> list[TaskAssignment]:
        return self._lookup_query.list_assignments_for_tasks(task_ids)

    def list_timesheet_assignment_contexts(
        self, *, project_id: str | None = None, resource_id: str | None = None
    ) -> list[TimesheetAssignmentContext]:
        return self._lookup_query.list_timesheet_assignment_contexts(
            project_id=project_id, resource_id=resource_id
        )

    def get_timesheet_assignment_context(
        self, assignment_id: str
    ) -> TimesheetAssignmentContext | None:
        return self._lookup_query.get_timesheet_assignment_context(assignment_id)

    def query_tasks(
        self,
        project_id: str | None = None,
        status: TaskStatus | None = None,
        resource_id: str | None = None,
        start_from: date | None = None,
        start_to: date | None = None,
        end_from: date | None = None,
        end_to: date | None = None,
    ) -> list[Task]:
        return self._lookup_query.query_tasks(
            project_id=project_id,
            status=status,
            resource_id=resource_id,
            start_from=start_from,
            start_to=start_to,
            end_from=end_from,
            end_to=end_to,
        )

    def query_workspace_page(
        self,
        *,
        project_id: str | None = None,
        resource_id: str | None = None,
        search_text: str = "",
        status: str = "all",
        priority: str = "all",
        schedule: str = "all",
        milestones_only: bool = False,
        page: int = 1,
        page_size: int = 25,
        as_of: date | None = None,
        sort_key: str = "wbsCode",
        sort_direction: str = "asc",
    ) -> TaskWorkspaceReadPage:
        return self._workspace_query.query_workspace_page(
            project_id=project_id,
            resource_id=resource_id,
            search_text=search_text,
            status=status,
            priority=priority,
            schedule=schedule,
            milestones_only=milestones_only,
            page=page,
            page_size=page_size,
            as_of=as_of,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def query_task_assignments_page(
        self, task_id: str, *, search_text: str = "", response_status: str = "all",
        page: int = 1, page_size: int = 25, sort_key: str = "resourceName",
        sort_direction: str = "asc",
    ) -> TaskAssignmentReadPage:
        return self._detail_query.query_task_assignments_page(
            task_id, search_text=search_text, response_status=response_status,
            page=page, page_size=page_size, sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def query_task_dependencies_page(
        self, task_id: str, *, search_text: str = "", direction: str = "all",
        dependency_type: str = "all", page: int = 1, page_size: int = 25,
        sort_key: str = "linkedTask", sort_direction: str = "asc",
    ) -> TaskDependencyReadPage:
        return self._detail_query.query_task_dependencies_page(
            task_id, search_text=search_text, direction=direction,
            dependency_type=dependency_type, page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=sort_direction,
        )

    def query_task_activity_page(
        self, task_id: str, *, search_text: str = "", category: str = "all",
        page: int = 1, page_size: int = 25,
    ) -> TaskActivityPage:
        return self._detail_query.query_task_activity_page(
            task_id, search_text=search_text, category=category,
            page=page, page_size=page_size,
        )

    def _task_uow(self, context: DomainEventContext | None = None):
        """Direct desktop-API commands (the normal, long-lived `TaskService`
        instance, always constructed with a `task_uow_factory`) get a real
        `SqlAlchemyTaskUnitOfWork` -- own commit, own precommit/postcommit
        dispatch. A participant-scoped `TaskService` (approval participants,
        Project's cascade-delete transaction, TimeEntry's transaction --
        constructed with `task_uow_factory=None`) gets
        `TaskParticipantUnitOfWork` instead: the canonical, permanent
        transaction-boundary-delegating counterpart (not a legacy shim -- see
        its own docstring), since that caller already owns the physical
        transaction."""
        from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
            TaskParticipantUnitOfWork,
        )

        if self._task_uow_factory is not None:
            return self._task_uow_factory.create(context=context or self._new_context())
        self._pending_task_events = []
        return TaskParticipantUnitOfWork(
            tasks=self._task_repo,
            assignments=self._assignment_repo,
            dependencies=self._dependency_repo,
            project_resources=self._project_resource_repo,
            enterprise_audit_service=self._enterprise_audit_service,
            activity_service=self._activity_service,
            collected_events=self._pending_task_events,
        )

    def _take_pending_task_events(self) -> tuple:
        events = tuple(self._pending_task_events)
        self._pending_task_events = []
        return events

    def _active_task_scope(self, *, operation_label: str):
        if self._tenant_context_service is None:
            raise RuntimeError("TaskService requires TenantContextService.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    def consume_last_overallocation_warning(self) -> str | None:
        warning = self._last_overallocation_warning
        self._last_overallocation_warning = None
        return warning

    def consume_last_skill_violation_warning(self) -> str | None:
        warning = self._last_skill_violation_warning
        self._last_skill_violation_warning = None
        return warning


__all__ = ["TaskService"]
