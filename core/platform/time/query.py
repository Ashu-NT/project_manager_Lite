from __future__ import annotations

from datetime import date, datetime, timezone

from core.platform.common.exceptions import NotFoundError
from core.platform.time.domain import TimeEntry, TimesheetPeriod
from core.platform.time.interfaces import (
    TimeEntryRepository,
    TimesheetPeriodRepository,
    WorkAllocationRepository,
)


class TimesheetQueryMixin:
    _work_allocation_repo: WorkAllocationRepository
    _time_entry_repo: TimeEntryRepository | None
    _timesheet_period_repo: TimesheetPeriodRepository | None

    def list_time_entries_for_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        self._require_time_read_permission("list time entries")
        work_allocation = self._work_allocation_repo.get(work_allocation_id)
        if not work_allocation:
            raise NotFoundError("Work allocation not found.", code="WORK_ALLOCATION_NOT_FOUND")
        if self._time_entry_repo is None:
            return []
        return self._time_entry_repo.list_by_work_allocation(work_allocation_id)

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return self.list_time_entries_for_work_allocation(assignment_id)

    def list_time_entries_for_work_allocation_period(
        self,
        work_allocation_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        self._require_time_read_permission("list period time entries")
        normalized_start, normalized_end = self._timesheet_period_bounds(period_start)
        return [
            entry
            for entry in self.list_time_entries_for_work_allocation(work_allocation_id)
            if normalized_start <= entry.entry_date <= normalized_end
        ]

    def list_time_entries_for_assignment_period(
        self,
        assignment_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        return self.list_time_entries_for_work_allocation_period(
            assignment_id,
            period_start=period_start,
        )

    def get_time_entry(self, entry_id: str) -> TimeEntry:
        self._require_time_read_permission("view time entry")
        return self._require_time_entry(entry_id)

    def get_timesheet_period(self, resource_id: str, *, period_start: date) -> TimesheetPeriod | None:
        self._require_time_read_permission("view timesheet period")
        return self._lookup_timesheet_period(resource_id=resource_id, period_start=period_start)

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        self._require_time_read_permission("list timesheet periods")
        if self._timesheet_period_repo is None:
            return []
        return self._timesheet_period_repo.list_by_resource(resource_id)

    def list_time_entries_for_resource_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        self._require_time_read_permission("list resource period time entries")
        if self._time_entry_repo is None:
            return []
        normalized_start, normalized_end = self._timesheet_period_bounds(period_start)
        rows: list[TimeEntry] = []
        for work_allocation in self._work_allocation_repo.list_by_resource(resource_id):
            for entry in self._time_entry_repo.list_by_work_allocation(work_allocation.id):
                if normalized_start <= entry.entry_date <= normalized_end:
                    rows.append(entry)
        rows.sort(key=lambda item: (item.entry_date, item.created_at or datetime.min.replace(tzinfo=timezone.utc)))
        return rows


__all__ = ["TimesheetQueryMixin"]
