from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSynchronizer,
    emit_cascade_schedule_changed,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskScheduleChanged,
    TaskScheduleChangeType,
)
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.contracts.ports.scheduling.schedule_change import (
    AppliedTaskScheduleChange,
    ApprovedTaskScheduleChange,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class ApprovedScheduleChangeHandler:
    """Internal task-owner command used only by governed approval orchestration."""

    def __init__(
        self,
        *,
        task_repo: TaskRepository,
        tenant_context_service: TenantContextService,
        work_calendar_engine: CalendarProtocol,
        scheduling_engine: SchedulingEngine | None,
        schedule_synchronizer: TaskScheduleSynchronizer,
        validation_policy: TaskValidationPolicy,
        uow_scope: TaskUowScope,
    ) -> None:
        self._task_repo = task_repo
        self._tenant_context_service = tenant_context_service
        self._work_calendar_engine = work_calendar_engine
        self._scheduling_engine = scheduling_engine
        self._schedule_synchronizer = schedule_synchronizer
        self._validation_policy = validation_policy
        self._uow_scope = uow_scope

    def _apply_approved_schedule_changes(
        self,
        changes: list[ApprovedTaskScheduleChange],
        *,
        actor_id: str,
    ) -> list[AppliedTaskScheduleChange]:
        """Always runs inside the caller's (ApprovalCommands's) own transaction
        -- this handler has a participant-scoped TaskUowScope, so `create()`
        joins the caller's transaction and never
        opens a second transaction. Recorded `TaskScheduleChanged` facts are
        collected via the TaskService facade immediately after
        this call returns, for the caller to fold into its own
        `ApprovalHandlerResult.domain_events`."""
        candidates = self._validate_approved_schedule_changes(changes)
        if not candidates:
            return []
        project_id = candidates[0][0].project_id
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="apply financial change schedule"
        )

        primary_task_ids = frozenset(candidate.id for _, candidate in candidates)
        with self._uow_scope.create() as uow:
            for _, candidate in candidates:
                uow.tasks.update(candidate)
            cascade_ids = self._schedule_synchronizer.sync_project_schedule(
                project_id, commit=False, exclude_task_ids=primary_task_ids
            )

            results: list[AppliedTaskScheduleChange] = []
            for change, candidate in candidates:
                applied = self._task_repo.get(candidate.id)
                if applied is None:
                    raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
                if (
                    applied.start_date != candidate.start_date
                    or applied.end_date != candidate.end_date
                ):
                    raise BusinessRuleError(
                        "Schedule dependencies or constraints prevent the approved task window "
                        f"({candidate.start_date}..{candidate.end_date} requested; "
                        f"{applied.start_date}..{applied.end_date} calculated).",
                        code="FINANCIAL_CHANGE_SCHEDULE_RESULT_CONFLICT",
                    )
                start_date = applied.start_date
                end_date = applied.end_date
                if start_date is None or end_date is None:
                    raise BusinessRuleError(
                        "Approved schedule result is missing its required dates.",
                        code="FINANCIAL_CHANGE_SCHEDULE_RESULT_CONFLICT",
                    )
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="task",
                    entity_id=applied.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    category="APPROVAL",
                    severity="low",
                    changed_fields={
                        "start_date": {"before": None, "after": start_date.isoformat()},
                        "end_date": {"before": None, "after": end_date.isoformat()},
                    },
                    metadata={
                        "action": "task.apply_financial_change_schedule",
                        "financial_change_impact_id": change.reference_id,
                        "actor_id": actor_id,
                    },
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="task.apply_financial_change_schedule",
                    entity_type="task",
                    entity_id=applied.id,
                    module="project_management",
                    workspace_id=project_id,
                    details={
                        "financial_change_impact_id": change.reference_id,
                        "start_date": start_date.isoformat(),
                        "finish_date": end_date.isoformat(),
                        "actor_id": actor_id,
                    },
                    commit=False,
                )
                uow.record_event(
                    TaskScheduleChanged(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=project_id,
                        task_id=applied.id,
                        change_type=TaskScheduleChangeType.APPROVED_SCHEDULE_APPLIED,
                        occurred_at=datetime.now(UTC),
                    )
                )
                results.append(
                    AppliedTaskScheduleChange(
                        reference_id=change.reference_id,
                        task_id=applied.id,
                        version=applied.version,
                        start_date=start_date,
                        finish_date=end_date,
                    )
                )
            emit_cascade_schedule_changed(
                uow, scope=scope, project_id=project_id, changed_task_ids=cascade_ids
            )
            uow.commit()
            return results

    def _validate_approved_schedule_changes(
        self, changes: list[ApprovedTaskScheduleChange]
    ) -> list[tuple[ApprovedTaskScheduleChange, Task]]:
        if not changes:
            return []
        project_ids = {change.project_id for change in changes}
        if len(project_ids) != 1:
            raise BusinessRuleError(
                "Approved schedule changes must belong to one project.",
                code="FINANCIAL_CHANGE_SCHEDULE_PROJECT_MISMATCH",
            )
        if len({change.task_id for change in changes}) != len(changes):
            raise BusinessRuleError(
                "A financial change may adjust each task schedule only once.",
                code="FINANCIAL_CHANGE_DUPLICATE_SCHEDULE_TARGET",
            )

        project_id = next(iter(project_ids))
        scheduler = getattr(self, "_scheduling_engine", None)
        calendar = (
            scheduler.calendar_for_project(project_id)
            if scheduler is not None
            else self._work_calendar_engine
        )
        tasks_by_id = {
            task.id: task
            for task in self._task_repo.list_by_ids([change.task_id for change in changes])
        }
        parents_with_children = {
            task.parent_task_id
            for task in self._task_repo.list_by_project(project_id)
            if task.parent_task_id is not None
        }
        candidates: list[tuple[ApprovedTaskScheduleChange, Task]] = []
        for change in changes:
            task = tasks_by_id.get(change.task_id)
            if task is None:
                raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
            if task.project_id != project_id:
                raise BusinessRuleError(
                    "Schedule target does not belong to the financial change project.",
                    code="FINANCIAL_CHANGE_TASK_PROJECT_MISMATCH",
                )
            if task.version != change.expected_version:
                raise ConcurrencyError(
                    "A schedule target changed after the financial change was drafted.",
                    code="FINANCIAL_CHANGE_SCHEDULE_BASE_STALE",
                )
            candidates.append(
                (
                    change,
                    self._schedule_candidate(
                        task,
                        change,
                        calendar,
                        has_children=task.id in parents_with_children,
                    ),
                )
            )
        return candidates

    def _schedule_candidate(
        self,
        task: Task,
        change: ApprovedTaskScheduleChange,
        calendar: CalendarProtocol,
        *,
        has_children: bool,
    ) -> Task:
        if has_children:
            raise BusinessRuleError(
                "Summary task schedules are rolled up from execution leaves.",
                code="TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN",
            )
        if (
            task.status in {TaskStatus.IN_PROGRESS, TaskStatus.DONE}
            or task.percent_complete > 0
            or task.actual_start is not None
            or task.actual_end is not None
        ):
            raise BusinessRuleError(
                "Started or completed tasks require remaining-work replanning, not a direct "
                "schedule-window change.",
                code="FINANCIAL_CHANGE_STARTED_TASK_SCHEDULE_FORBIDDEN",
            )

        start = change.start_date or task.start_date
        finish = change.finish_date
        if start is None:
            raise ValidationError(
                "A schedule change requires a start date.",
                code="FINANCIAL_CHANGE_SCHEDULE_START_REQUIRED",
            )
        if not calendar.is_working_day(start):
            raise ValidationError(
                "Schedule change start must be a project working day.",
                code="FINANCIAL_CHANGE_SCHEDULE_START_NOT_WORKING_DAY",
            )
        if finish is None:
            duration = task.duration_days
            if duration is None and task.start_date and task.end_date:
                duration = max(
                    0,
                    calendar.working_days_between(task.start_date, task.end_date),
                )
            finish = calendar.add_working_days(start, duration or 0)
        if finish < start:
            raise ValidationError(
                "Schedule change finish cannot precede start.",
                code="FINANCIAL_CHANGE_SCHEDULE_PERIOD_INVALID",
            )
        if not calendar.is_working_day(finish):
            raise ValidationError(
                "Schedule change finish must be a project working day.",
                code="FINANCIAL_CHANGE_SCHEDULE_FINISH_NOT_WORKING_DAY",
            )
        duration = max(
            0,
            calendar.working_days_between(start, finish),
        )
        candidate = replace(
            task,
            start_date=start,
            end_date=finish,
            duration_days=duration,
        )
        self._validation_policy.validate_task_within_project_dates(
            candidate.project_id, candidate.start_date, candidate.end_date
        )
        return candidate


__all__ = [
    "ApprovedScheduleChangeHandler",
]
