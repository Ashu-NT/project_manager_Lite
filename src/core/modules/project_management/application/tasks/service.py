from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.resources.capacity.task_assignment_capacity_service import (
    TaskAssignmentCapacityFact,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.scheduling.models.leveling import (
    LevelingProposal,
)
from src.core.modules.project_management.application.tasks.commands.approved_schedule_change import (
    ApprovedScheduleChangeHandler,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentActionContext,
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.deletion import (
    TaskDeletionCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.dependency import (
    TaskDependencyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy import (
    TaskHierarchyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy_support import (
    TaskHierarchyPolicy,
)
from src.core.modules.project_management.application.tasks.commands.identity import (
    TaskCodePolicy,
)
from src.core.modules.project_management.application.tasks.commands.lifecycle import (
    TaskLifecycleCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.progress import (
    TaskProgressCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.resource_leveling_apply import (
    ResourceLevelingCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSynchronizer,
)
from src.core.modules.project_management.application.tasks.commands.scheduling_constraint import (
    TaskSchedulingConstraintHandler,
)
from src.core.modules.project_management.application.tasks.commands.time_entries import (
    TaskTimeEntryHandler,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    DependencyDiagnostic,
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.dependency_query import (
    TaskDependencyQueryHandler,
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
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.contracts.ports.schedule_change import (
    AppliedTaskScheduleChange,
    ApprovedTaskScheduleChange,
)
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskActivityPage,
    TaskAssignmentReadPage,
    TaskDependencyReadPage,
    TaskWorkspaceReader,
    TaskWorkspaceReadPage,
)
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskTimeEntriesPage,
    TaskTimeSummaryFact,
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
from src.core.modules.project_management.domain.enums import (
    ConstraintType,
    DependencyType,
    TaskStatus,
)
from src.core.modules.project_management.domain.tasks.hierarchy import (
    TaskHierarchyNode,
    TaskHierarchyRollup,
)
from src.core.modules.project_management.domain.tasks.task import (
    Task,
    TaskAssignment,
    TaskDependency,
)
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.time_management.time import TimesheetPeriodAggregate
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import TimeEntry, TimesheetPeriod
from src.core.shared.events.domain_event_context import DomainEventContext


class TaskService(
    ProjectManagementModuleGuardMixin,
):
    """Task application service orchestrator."""

    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        time_entry_repo: TimeEntryRepository | None,
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
        hierarchy_policy: TaskHierarchyPolicy,
        task_uow_scope: TaskUowScope,
        deletion_handler: TaskDeletionCommandHandler,
        progress_handler: TaskProgressCommandHandler,
        time_entry_handler: TaskTimeEntryHandler,
        approved_schedule_change_handler: ApprovedScheduleChangeHandler,
        hierarchy_command_handler: TaskHierarchyCommandHandler,
        scheduling_constraint_handler: TaskSchedulingConstraintHandler,
        resource_leveling_handler: ResourceLevelingCommandHandler,
        lifecycle_handler: TaskLifecycleCommandHandler,
        dependency_command_handler: TaskDependencyCommandHandler,
        dependency_query_handler: TaskDependencyQueryHandler,
        assignment_handler: TaskAssignmentCommandHandler,
    ):
        self._session: Session = session
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._time_entry_repo = time_entry_repo
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
        self._hierarchy_policy = hierarchy_policy
        self._enterprise_resource_availability_service = enterprise_resource_availability_service
        self._task_uow_scope = task_uow_scope
        self._deletion_handler = deletion_handler
        self._progress_handler = progress_handler
        self._time_entry_handler = time_entry_handler
        self._approved_schedule_change_handler = approved_schedule_change_handler
        self._hierarchy_command_handler = hierarchy_command_handler
        self._scheduling_constraint_handler = scheduling_constraint_handler
        self._resource_leveling_handler = resource_leveling_handler
        self._lifecycle_handler = lifecycle_handler
        self._dependency_command_handler = dependency_command_handler
        self._dependency_query_handler = dependency_query_handler
        self._assignment_handler = assignment_handler
        self._enterprise_audit_service: EnterpriseAuditService | None = enterprise_audit_service

    def delete_task(self, task_id: str) -> None:
        self._deletion_handler.delete_task(task_id)

    def assign_resource(
        self, task_id: str, resource_id: str, allocation_percent: float = 100.0
    ) -> TaskAssignment:
        return self._assignment_handler.assign_resource(task_id, resource_id, allocation_percent)

    def assign_project_resource(
        self,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
        *,
        allocated_planned_hours: Decimal = Decimal(0),
    ) -> TaskAssignment:
        return self._assignment_handler.assign_project_resource(
            task_id,
            project_resource_id,
            allocation_percent,
            allocated_planned_hours=allocated_planned_hours,
        )

    def unassign_resource(self, assignment_id: str) -> None:
        self._assignment_handler.unassign_resource(assignment_id)

    def list_assignments_for_task(self, task_id: str) -> list[TaskAssignment]:
        return self._assignment_handler.list_assignments_for_task(task_id)

    def get_assignment(self, assignment_id: str) -> TaskAssignment | None:
        return self._assignment_handler.get_assignment(assignment_id)

    def get_task_time_summary(self, task_id: str) -> TaskTimeSummaryFact:
        return self._assignment_handler.get_task_time_summary(task_id)

    def set_assignment_hours(self, assignment_id: str, hours_logged: Decimal) -> TaskAssignment:
        return self._assignment_handler.set_assignment_hours(assignment_id, hours_logged)

    def set_assignment_allocation(
        self, assignment_id: str, allocation_percent: float, *, expected_version: int
    ) -> TaskAssignment:
        return self._assignment_handler.set_assignment_allocation(
            assignment_id, allocation_percent, expected_version=expected_version
        )

    def update_assignment_planned_hours(
        self,
        assignment_id: str,
        *,
        allocated_planned_hours: Decimal,
        expected_assignment_version: int,
        expected_project_resource_version: int,
    ) -> TaskAssignment:
        return self._assignment_handler.update_assignment_planned_hours(
            assignment_id,
            allocated_planned_hours=allocated_planned_hours,
            expected_assignment_version=expected_assignment_version,
            expected_project_resource_version=expected_project_resource_version,
        )

    def preview_assignment_capacity(
        self,
        task_id: str,
        resource_id: str,
        *,
        proposed_allocation_percent: float = 100.0,
        exclude_assignment_id: str | None = None,
    ) -> TaskAssignmentCapacityFact | None:
        return self._assignment_handler.preview_assignment_capacity(
            task_id,
            resource_id,
            proposed_allocation_percent=proposed_allocation_percent,
            exclude_assignment_id=exclude_assignment_id,
        )

    def get_assignment_action_context(
        self, assignment_id: str
    ) -> TaskAssignmentActionContext:
        return self._assignment_handler.get_assignment_action_context(assignment_id)

    def accept_assignment(self, assignment_id: str) -> TaskAssignment:
        return self._assignment_handler.accept_assignment(assignment_id)

    def decline_assignment(
        self, assignment_id: str, reason: str | None = None
    ) -> TaskAssignment:
        return self._assignment_handler.decline_assignment(assignment_id, reason)

    def get_dependency(self, dep_id: str) -> TaskDependency | None:
        return self._dependency_query_handler.get_dependency(dep_id)

    def list_dependencies_for_task(self, task_id: str) -> list[TaskDependency]:
        return self._dependency_query_handler.list_dependencies_for_task(task_id)

    def list_dependencies_for_project(self, project_id: str) -> list[TaskDependency]:
        return self._dependency_query_handler.list_dependencies_for_project(project_id)

    def add_dependency(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
    ) -> TaskDependency:
        return self._dependency_command_handler.add_dependency(
            predecessor_id, successor_id, dependency_type, lag_days
        )

    def remove_dependency(self, dep_id: str) -> None:
        self._dependency_command_handler.remove_dependency(dep_id)

    def update_dependency(
        self,
        dep_id: str,
        *,
        dependency_type: DependencyType | None = None,
        lag_days: int | None = None,
        expected_version: int | None = None,
    ) -> TaskDependency:
        return self._dependency_command_handler.update_dependency(
            dep_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            expected_version=expected_version,
        )

    def _apply_dependency_add_decision(
        self,
        *,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType,
        lag_days: int,
    ) -> TaskDependency:
        return self._dependency_command_handler._apply_dependency_add_decision(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )

    def _apply_dependency_remove_decision(self, *, dependency_id: str) -> None:
        self._dependency_command_handler._apply_dependency_remove_decision(
            dependency_id=dependency_id
        )

    def _apply_dependency_update_decision(
        self,
        *,
        dependency_id: str,
        dependency_type: DependencyType,
        lag_days: int,
        expected_version: int | None = None,
    ) -> TaskDependency:
        return self._dependency_command_handler._apply_dependency_update_decision(
            dependency_id=dependency_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            expected_version=expected_version,
        )

    def create_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: int = 0,
        deadline: date | None = None,
        code: str = "",
        parent_task_id: str | None = None,
        wbs_code: str = "",
        sort_order: int | None = None,
        is_milestone: bool = False,
        constraint_type: ConstraintType | None = None,
        constraint_date: date | None = None,
    ) -> Task:
        return self._lifecycle_handler.create_task(
            project_id,
            name,
            description=description,
            start_date=start_date,
            duration_days=duration_days,
            status=status,
            priority=priority,
            deadline=deadline,
            code=code,
            parent_task_id=parent_task_id,
            wbs_code=wbs_code,
            sort_order=sort_order,
            is_milestone=is_milestone,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
        )

    def update_task(
        self,
        task_id: str,
        name: str | None = None,
        description: str | None = None,
        start_date: date | None = None,
        duration_days: int | None = None,
        status: TaskStatus | None = None,
        priority: int | None = None,
        deadline: date | None = None,
        expected_version: int | None = None,
        code: str | None = None,
        is_milestone: bool | None = None,
    ) -> Task:
        return self._lifecycle_handler.update_task(
            task_id,
            name=name,
            description=description,
            start_date=start_date,
            duration_days=duration_days,
            status=status,
            priority=priority,
            deadline=deadline,
            expected_version=expected_version,
            code=code,
            is_milestone=is_milestone,
        )

    def update_task_scheduling_constraint(
        self,
        task_id: str,
        *,
        constraint_type: ConstraintType | None,
        constraint_date: date | None,
        expected_version: int | None = None,
    ) -> Task:
        return self._scheduling_constraint_handler.update_task_scheduling_constraint(
            task_id,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
            expected_version=expected_version,
        )

    def _apply_task_scheduling_constraint_decision(
        self,
        *,
        task_id: str,
        constraint_type: ConstraintType | None,
        constraint_date: date | None,
        expected_version: int | None = None,
    ) -> Task:
        return self._scheduling_constraint_handler._apply_task_scheduling_constraint_decision(
            task_id=task_id,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
            expected_version=expected_version,
        )

    def _validate_constraint_date_is_working_day(self, candidate: Task) -> None:
        self._scheduling_constraint_handler._validate_constraint_date_is_working_day(candidate)

    def build_resource_leveling_preview(self, project_id: str) -> LevelingProposal | None:
        return self._resource_leveling_handler.build_resource_leveling_preview(project_id)

    def apply_resource_leveling_plan(
        self, project_id: str, proposal: LevelingProposal
    ) -> list[Task]:
        return self._resource_leveling_handler.apply_resource_leveling_plan(
            project_id, proposal
        )

    def _apply_resource_leveling_plan_decision(
        self, *, project_id: str, moves: list[dict], schedule_fingerprint: str
    ) -> list[Task]:
        return self._resource_leveling_handler._apply_resource_leveling_plan_decision(
            project_id=project_id,
            moves=moves,
            schedule_fingerprint=schedule_fingerprint,
        )

    def _validate_approved_schedule_changes(
        self, changes: list[ApprovedTaskScheduleChange]
    ) -> list[tuple[ApprovedTaskScheduleChange, Task]]:
        return self._approved_schedule_change_handler._validate_approved_schedule_changes(
            changes
        )

    def _apply_approved_schedule_changes(
        self, changes: list[ApprovedTaskScheduleChange], *, actor_id: str
    ) -> list[AppliedTaskScheduleChange]:
        return self._approved_schedule_change_handler._apply_approved_schedule_changes(
            changes, actor_id=actor_id
        )

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        return self._deletion_handler.delete_tasks(task_ids)

    def move_task(
        self,
        task_id: str,
        *,
        parent_task_id: str | None,
        wbs_code: str | None = None,
        sort_order: int | None = None,
        expected_version: int | None = None,
    ) -> Task:
        return self._hierarchy_command_handler.move_task(
            task_id,
            parent_task_id=parent_task_id,
            wbs_code=wbs_code,
            sort_order=sort_order,
            expected_version=expected_version,
        )

    def recode_task(
        self, task_id: str, wbs_code: str, *, expected_version: int | None = None
    ) -> Task:
        return self._hierarchy_command_handler.recode_task(
            task_id, wbs_code, expected_version=expected_version
        )

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        self._progress_handler.set_status(task_id, status)

    def set_tasks_status(
        self,
        task_ids: tuple[str, ...],
        status: TaskStatus,
        *,
        reopen_percent_complete: float | None = None,
    ) -> list[Task]:
        return self._progress_handler.set_tasks_status(
            task_ids, status, reopen_percent_complete=reopen_percent_complete
        )

    def update_progress(
        self,
        task_id: str,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> Task:
        return self._progress_handler.update_progress(
            task_id,
            percent_complete=percent_complete,
            actual_start=actual_start,
            actual_end=actual_end,
            status=status,
            expected_version=expected_version,
        )

    def initialize_timesheet_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return self._time_entry_handler.initialize_timesheet_for_assignment(assignment_id)

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return self._time_entry_handler.list_time_entries_for_assignment(assignment_id)

    def list_time_entries_for_task_page(
        self,
        task_id: str,
        *,
        resource_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_direction: str = "desc",
    ) -> TaskTimeEntriesPage:
        return self._time_entry_handler.list_time_entries_for_task_page(
            task_id,
            resource_id=resource_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
            sort_direction=sort_direction,
        )

    def list_time_entries_for_assignment_period(
        self, assignment_id: str, *, period_start: date
    ) -> list[TimeEntry]:
        return self._time_entry_handler.list_time_entries_for_assignment_period(
            assignment_id, period_start=period_start
        )

    def get_time_entry(self, entry_id: str) -> TimeEntry:
        return self._time_entry_handler.get_time_entry(entry_id)

    def add_time_entry(
        self, assignment_id: str, *, entry_date: date, hours: float, note: str = ""
    ) -> TimeEntry:
        return self._time_entry_handler.add_time_entry(
            assignment_id, entry_date=entry_date, hours=hours, note=note
        )

    def update_time_entry(
        self,
        entry_id: str,
        *,
        expected_version: int,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ) -> TimeEntry:
        return self._time_entry_handler.update_time_entry(
            entry_id,
            expected_version=expected_version,
            entry_date=entry_date,
            hours=hours,
            note=note,
        )

    def delete_time_entry(self, entry_id: str, *, expected_version: int) -> None:
        self._time_entry_handler.delete_time_entry(entry_id, expected_version=expected_version)

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        return self._time_entry_handler.list_timesheet_periods_for_resource(resource_id)

    def list_time_entries_for_resource_period(
        self, resource_id: str, *, period_start: date
    ) -> list[TimeEntry]:
        return self._time_entry_handler.list_time_entries_for_resource_period(
            resource_id, period_start=period_start
        )

    def submit_timesheet_period(
        self, resource_id: str, *, period_start: date, note: str = ""
    ) -> TimesheetPeriodAggregate:
        return self._time_entry_handler.submit_timesheet_period(
            resource_id, period_start=period_start, note=note
        )

    def approve_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str = ""
    ) -> TimesheetPeriodAggregate:
        return self._time_entry_handler.approve_timesheet_period(
            period_id, expected_version=expected_version, note=note
        )

    def reject_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str
    ) -> TimesheetPeriodAggregate:
        return self._time_entry_handler.reject_timesheet_period(
            period_id, expected_version=expected_version, note=note
        )

    def lock_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str = ""
    ) -> TimesheetPeriodAggregate:
        return self._time_entry_handler.lock_timesheet_period(
            period_id, expected_version=expected_version, note=note
        )

    def unlock_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str = ""
    ) -> TimesheetPeriodAggregate:
        return self._time_entry_handler.unlock_timesheet_period(
            period_id, expected_version=expected_version, note=note
        )

    def reopen_approved_timesheet_period_for_correction(
        self, period_id: str, *, expected_version: int, note: str
    ) -> TimesheetPeriodAggregate:
        return self._time_entry_handler.reopen_approved_timesheet_period_for_correction(
            period_id, expected_version=expected_version, note=note
        )

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

    def _is_task_wbs_integrity_error(self, exc: IntegrityError) -> bool:
        return self._hierarchy_policy._is_task_wbs_integrity_error(exc)

    def _children_by_parent(self, tasks: list[Task]) -> dict[str | None, list[Task]]:
        return self._hierarchy_policy._children_by_parent(tasks)

    def _require_wbs_parent(
        self,
        *,
        project_id: str,
        parent_task_id: str | None,
        moving_task_id: str | None = None,
        tasks: list[Task] | None = None,
    ) -> Task | None:
        return self._hierarchy_policy._require_wbs_parent(
            project_id=project_id,
            parent_task_id=parent_task_id,
            moving_task_id=moving_task_id,
            tasks=tasks,
        )

    def _assert_parent_has_no_direct_execution(self, parent: Task) -> None:
        self._hierarchy_policy._assert_parent_has_no_direct_execution(parent)

    def _next_wbs_code(self, parent: Task | None, siblings: list[Task]) -> str:
        return self._hierarchy_policy._next_wbs_code(parent, siblings)

    def _validate_wbs_code_for_parent(self, code: str, parent: Task | None) -> str:
        return self._hierarchy_policy._validate_wbs_code_for_parent(code, parent)

    def _prepare_new_task_hierarchy(
        self,
        task: Task,
        *,
        parent_task_id: str | None,
        wbs_code: str,
        sort_order: int | None,
    ) -> Task:
        return self._hierarchy_policy._prepare_new_task_hierarchy(
            task,
            parent_task_id=parent_task_id,
            wbs_code=wbs_code,
            sort_order=sort_order,
        )

    def _require_leaf_task(self, task: Task, *, operation_label: str) -> None:
        self._hierarchy_policy._require_leaf_task(task, operation_label=operation_label)

    def _resequence_for_new_task(self, task: Task) -> Task:
        return self._hierarchy_policy._resequence_for_new_task(task)

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
        return self._task_uow_scope.create(context)

    def _take_pending_task_events(self) -> tuple:
        return self._task_uow_scope.take_pending_events()

    def _active_task_scope(self, *, operation_label: str):
        if self._tenant_context_service is None:
            raise RuntimeError("TaskService requires TenantContextService.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    def consume_last_overallocation_warning(self) -> str | None:
        return self._assignment_handler.consume_last_overallocation_warning()

    def consume_last_skill_violation_warning(self) -> str | None:
        return self._assignment_handler.consume_last_skill_violation_warning()


__all__ = ["TaskService"]
