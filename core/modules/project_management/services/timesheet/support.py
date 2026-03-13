from __future__ import annotations

import calendar
from datetime import date, datetime, timezone

from core.modules.project_management.domain.task import Task
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.interfaces import (
    AssignmentRepository,
    ResourceRepository,
    TaskRepository,
    TimeEntryRepository,
    TimesheetPeriodRepository,
)
from core.platform.common.models import TaskAssignment, TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


class TimesheetSupportMixin:
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _task_repo: TaskRepository
    _time_entry_repo: TimeEntryRepository | None
    _timesheet_period_repo: TimesheetPeriodRepository | None

    def _require_time_entry(self, entry_id: str) -> TimeEntry:
        if self._time_entry_repo is None:
            raise NotFoundError("Time entry repository is not configured.", code="TIME_ENTRY_REPO_MISSING")
        entry = self._time_entry_repo.get(entry_id)
        if not entry:
            raise NotFoundError("Time entry not found.", code="TIME_ENTRY_NOT_FOUND")
        return entry

    def _load_assignment_context(self, assignment_id: str):
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        task = self._task_repo.get(assignment.task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        resource = self._resource_repo.get(assignment.resource_id)
        return assignment, task, resource

    def _sync_assignment_hours_from_entries(self, assignment_id: str) -> None:
        if self._time_entry_repo is None:
            return
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        entries = self._time_entry_repo.list_by_assignment(assignment_id)
        assignment.hours_logged = sum(float(item.hours or 0.0) for item in entries)
        self._assignment_repo.update(assignment)

    def _seed_legacy_hours_entry(self, assignment: TaskAssignment, task: Task) -> TimeEntry | None:
        if self._time_entry_repo is None:
            return None
        if self._time_entry_repo.list_by_assignment(assignment.id):
            return None
        hours = float(getattr(assignment, "hours_logged", 0.0) or 0.0)
        if hours <= 0:
            return None
        legacy_date = self._resolve_legacy_time_entry_date(task)
        self._ensure_timesheet_period_editable(
            resource_id=assignment.resource_id,
            entry_date=legacy_date,
            operation_label="seed legacy timesheet entry",
        )
        seeded_entry = TimeEntry.create(
            assignment_id=assignment.id,
            entry_date=legacy_date,
            hours=hours,
            note="Opening balance migrated from existing logged hours.",
            author_username="system",
        )
        self._time_entry_repo.add(seeded_entry)
        self._session.flush()
        self._sync_assignment_hours_from_entries(assignment.id)
        return seeded_entry

    @staticmethod
    def _resolve_legacy_time_entry_date(task: Task) -> date:
        return task.actual_start or task.start_date or date.today()

    @staticmethod
    def _build_time_entry_audit_details(
        *,
        assignment: TaskAssignment,
        task: Task,
        resource_name: str,
        entry: TimeEntry,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        details: dict[str, object] = {
            "task_name": task.name,
            "resource_name": resource_name or assignment.resource_id,
            "hours": entry.hours,
            "entry_date": str(entry.entry_date),
        }
        for key, value in (extra or {}).items():
            if value is not None:
                details[key] = value
        return details

    @staticmethod
    def _validate_time_entry_hours(hours: float) -> float:
        resolved = float(hours or 0.0)
        if resolved <= 0:
            raise ValidationError("Time entry hours must be greater than zero.")
        return resolved

    def _require_timesheet_period(self, period_id: str) -> TimesheetPeriod:
        if self._timesheet_period_repo is None:
            raise NotFoundError("Timesheet period repository is not configured.", code="TIMESHEET_PERIOD_REPO_MISSING")
        period = self._timesheet_period_repo.get(period_id)
        if not period:
            raise NotFoundError("Timesheet period not found.", code="TIMESHEET_PERIOD_NOT_FOUND")
        return period

    def _get_or_create_timesheet_period(self, *, resource_id: str, period_start: date) -> TimesheetPeriod:
        if self._timesheet_period_repo is None:
            raise ValidationError("Timesheet period repository is not configured.")
        normalized_start, normalized_end = self._timesheet_period_bounds(period_start)
        period = self._timesheet_period_repo.get_by_resource_period(resource_id, normalized_start)
        if period is not None:
            return period
        period = TimesheetPeriod.create(
            resource_id=resource_id,
            period_start=normalized_start,
            period_end=normalized_end,
        )
        self._timesheet_period_repo.add(period)
        self._session.flush()
        return period

    def _ensure_timesheet_period_editable(
        self,
        *,
        resource_id: str,
        entry_date: date,
        operation_label: str,
    ) -> None:
        period = self.get_timesheet_period(resource_id, period_start=entry_date)
        if period is None:
            return
        if period.status not in {
            TimesheetPeriodStatus.SUBMITTED,
            TimesheetPeriodStatus.APPROVED,
            TimesheetPeriodStatus.LOCKED,
        }:
            return
        raise ValidationError(
            f"Cannot {operation_label}: timesheet period {period.period_start.isoformat()} is {period.status.value.lower()}."
        )

    @staticmethod
    def _timesheet_period_bounds(period_date: date) -> tuple[date, date]:
        normalized_start = period_date.replace(day=1)
        last_day = calendar.monthrange(normalized_start.year, normalized_start.month)[1]
        normalized_end = normalized_start.replace(day=last_day)
        return normalized_start, normalized_end

    @staticmethod
    def _sum_entry_hours(entries: list[TimeEntry]) -> float:
        return sum(float(item.hours or 0.0) for item in entries)

    def _build_timesheet_period_audit_details(
        self,
        *,
        period: TimesheetPeriod,
        entry_count: int,
        total_hours: float,
    ) -> dict[str, object]:
        resource = self._resource_repo.get(period.resource_id)
        return {
            "resource_name": resource.name if resource is not None else period.resource_id,
            "period_start": str(period.period_start),
            "period_end": str(period.period_end),
            "status": period.status.value,
            "entry_count": entry_count,
            "total_hours": total_hours,
        }


__all__ = ["TimesheetSupportMixin"]
