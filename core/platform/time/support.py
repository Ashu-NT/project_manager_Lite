from __future__ import annotations

import calendar
from datetime import date
from typing import Protocol

from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.interfaces import EmployeeRepository
from core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus
from core.platform.time.interfaces import (
    TimeEntryRepository,
    TimesheetPeriodRepository,
    WorkAssignmentRecord,
    WorkAssignmentRepository,
    WorkResourceRecord,
    WorkResourceRepository,
    WorkTaskRecord,
    WorkTaskRepository,
)


class _TaskSeedContext(Protocol):
    project_id: str
    name: str
    start_date: date | None
    actual_start: date | None


class TimesheetSupportMixin:
    _assignment_repo: WorkAssignmentRepository
    _resource_repo: WorkResourceRepository
    _task_repo: WorkTaskRepository
    _employee_repo: EmployeeRepository | None
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

    def _resolve_work_entry_context(
        self,
        *,
        assignment: WorkAssignmentRecord,
        resource: WorkResourceRecord | None,
    ) -> dict[str, str | None]:
        employee_id = getattr(resource, "employee_id", None) if resource is not None else None
        department_id = None
        department_name = ""
        site_id = None
        site_name = ""
        if employee_id and self._employee_repo is not None:
            employee = self._employee_repo.get(employee_id)
            if employee is not None:
                department_id = getattr(employee, "department_id", None)
                department_name = (employee.department or "").strip()
                site_id = getattr(employee, "site_id", None)
                site_name = (getattr(employee, "site_name", "") or "").strip()
        return {
            "owner_type": "task_assignment",
            "owner_id": assignment.id,
            "employee_id": employee_id,
            "department_id": department_id,
            "department_name": department_name,
            "site_id": site_id,
            "site_name": site_name,
        }

    def _sync_assignment_hours_from_entries(self, assignment_id: str) -> None:
        if self._time_entry_repo is None:
            return
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        entries = self._time_entry_repo.list_by_assignment(assignment_id)
        assignment.hours_logged = sum(float(item.hours or 0.0) for item in entries)
        self._assignment_repo.update(assignment)

    def _seed_legacy_hours_entry(self, assignment: WorkAssignmentRecord, task: _TaskSeedContext) -> TimeEntry | None:
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
            **self._resolve_work_entry_context(assignment=assignment, resource=self._resource_repo.get(assignment.resource_id)),
        )
        self._time_entry_repo.add(seeded_entry)
        self._session.flush()
        self._sync_assignment_hours_from_entries(assignment.id)
        return seeded_entry

    @staticmethod
    def _resolve_legacy_time_entry_date(task: _TaskSeedContext) -> date:
        return task.actual_start or task.start_date or date.today()

    @staticmethod
    def _build_time_entry_audit_details(
        *,
        assignment: WorkAssignmentRecord,
        task: WorkTaskRecord,
        resource_name: str,
        entry: TimeEntry,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        details: dict[str, object] = {
            "task_name": task.name,
            "resource_name": resource_name or assignment.resource_id,
            "hours": entry.hours,
            "entry_date": str(entry.entry_date),
            "owner_type": entry.owner_type,
        }
        if entry.owner_id:
            details["owner_id"] = entry.owner_id
        if entry.employee_id:
            details["employee_id"] = entry.employee_id
        if getattr(entry, "department_id", None):
            details["department_id"] = entry.department_id
        if entry.department_name:
            details["department_name"] = entry.department_name
        if getattr(entry, "site_id", None):
            details["site_id"] = entry.site_id
        if entry.site_name:
            details["site_name"] = entry.site_name
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
        project_ids: list[str] | None = None,
    ) -> dict[str, object]:
        resource = self._resource_repo.get(period.resource_id)
        details: dict[str, object] = {
            "resource_name": resource.name if resource is not None else period.resource_id,
            "period_start": str(period.period_start),
            "period_end": str(period.period_end),
            "status": period.status.value,
            "entry_count": entry_count,
            "total_hours": total_hours,
        }
        normalized_project_ids = [item for item in (project_ids or []) if str(item).strip()]
        if len(normalized_project_ids) == 1:
            details["project_id"] = normalized_project_ids[0]
        elif normalized_project_ids:
            details["project_ids"] = normalized_project_ids
        return details

    def _project_ids_for_entries(self, entries: list[TimeEntry]) -> list[str]:
        project_ids: set[str] = set()
        for entry in entries:
            assignment = self._assignment_repo.get(entry.assignment_id)
            if assignment is None:
                continue
            task = self._task_repo.get(assignment.task_id)
            if task is None or not getattr(task, "project_id", None):
                continue
            project_ids.add(str(task.project_id))
        return sorted(project_ids)


__all__ = ["TimesheetSupportMixin"]
