from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.contracts.schedule_change import (
    AppliedTaskScheduleChange,
    ApprovedTaskScheduleChange,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.activity import record_activity


class ApprovedScheduleChangeMixin:
    """Internal task-owner command used only by governed approval orchestration."""

    def _apply_approved_schedule_changes(
        self,
        changes: list[ApprovedTaskScheduleChange],
        *,
        actor_id: str,
        commit: bool = False,
    ) -> list[AppliedTaskScheduleChange]:
        candidates = self._validate_approved_schedule_changes(changes)
        if not candidates:
            return []
        project_id = candidates[0][0].project_id

        try:
            for _, candidate in candidates:
                self._task_repo.update(candidate)
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
                record_activity(
                    self,
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
                results.append(
                    AppliedTaskScheduleChange(
                        reference_id=change.reference_id,
                        task_id=applied.id,
                        version=applied.version,
                        start_date=applied.start_date,
                        finish_date=applied.end_date,
                    )
                )
            if commit:
                self._session.commit()
            else:
                self._session.flush()
            return results
        except Exception:
            if commit:
                self._session.rollback()
            raise

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
            candidates.append((change, self._schedule_candidate(task, change)))
        return candidates

    def _schedule_candidate(
        self, task: Task, change: ApprovedTaskScheduleChange
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
        if not self._work_calendar_engine.is_working_day(start):
            raise ValidationError(
                "Schedule change start must be a project working day.",
                code="FINANCIAL_CHANGE_SCHEDULE_START_NOT_WORKING_DAY",
            )
        if finish is None:
            duration = task.duration_days
            if duration is None and task.start_date and task.end_date:
                duration = max(
                    0,
                    self._work_calendar_engine.working_days_between(
                        task.start_date, task.end_date
                    ),
                )
            finish = self._work_calendar_engine.add_working_days(start, duration or 0)
        if finish < start:
            raise ValidationError(
                "Schedule change finish cannot precede start.",
                code="FINANCIAL_CHANGE_SCHEDULE_PERIOD_INVALID",
            )
        if not self._work_calendar_engine.is_working_day(finish):
            raise ValidationError(
                "Schedule change finish must be a project working day.",
                code="FINANCIAL_CHANGE_SCHEDULE_FINISH_NOT_WORKING_DAY",
            )
        duration = max(
            0,
            self._work_calendar_engine.working_days_between(start, finish),
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
