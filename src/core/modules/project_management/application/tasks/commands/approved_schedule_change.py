from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.core.modules.project_management.application.tasks.task_events import (
    TaskScheduleChangeType,
    TaskScheduleChanged,
)
from src.core.modules.project_management.contracts.ports.schedule_change import (
    AppliedTaskScheduleChange,
    ApprovedTaskScheduleChange,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class ApprovedScheduleChangeMixin:
    """Internal task-owner command used only by governed approval orchestration."""

    def _apply_approved_schedule_changes(
        self,
        changes: list[ApprovedTaskScheduleChange],
        *,
        actor_id: str,
    ) -> list[AppliedTaskScheduleChange]:
        """Always runs inside the caller's (ApprovalService's) own transaction
        -- this TaskService instance is participant-scoped (`task_uow_factory=
        None`), so `self._task_uow()` returns the passthrough shim and never
        opens a second transaction. Recorded `TaskScheduleChanged` facts are
        collected via `self._take_pending_task_events()` immediately after
        this call returns, for the caller to fold into its own
        `ApprovalHandlerResult.domain_events`."""
        candidates = self._validate_approved_schedule_changes(changes)
        if not candidates:
            return []
        project_id = candidates[0][0].project_id
        scope = self._active_task_scope(operation_label="apply financial change schedule")

        with self._task_uow() as uow:
            for _, candidate in candidates:
                uow.tasks.update(candidate)
            self._sync_project_schedule(project_id, commit=False)

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
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="task",
                    entity_id=applied.id,
                    module="project_management",
                    organization_id=scope.organization_id,
                    severity="low",
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
                        "start_date": applied.start_date.isoformat(),
                        "finish_date": applied.end_date.isoformat(),
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
                        occurred_at=datetime.now(timezone.utc),
                    )
                )
                results.append(
                    AppliedTaskScheduleChange(
                        reference_id=change.reference_id,
                        task_id=applied.id,
                        version=applied.version,
                        start_date=applied.start_date,
                        finish_date=applied.end_date,
                    )
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
        candidates: list[tuple[ApprovedTaskScheduleChange, Task]] = []
        for change in changes:
            task = self._task_repo.get(change.task_id)
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
            candidates.append((change, self._schedule_candidate(task, change, calendar)))
        return candidates

    def _schedule_candidate(
        self,
        task: Task,
        change: ApprovedTaskScheduleChange,
        calendar: CalendarProtocol,
    ) -> Task:
        if self._task_repo.list_children(task.project_id, task.id):
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
        self._validate_task_within_project_dates(
            candidate.project_id, candidate.start_date, candidate.end_date
        )
        return candidate


__all__ = [
    "ApprovedScheduleChangeMixin",
]
