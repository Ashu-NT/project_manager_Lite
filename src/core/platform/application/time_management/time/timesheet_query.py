from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
    TimesheetPeriodRepository,
    WorkAllocationRepository,
)
from src.core.platform.domain.time_management.time import (
    TimeEntry,
    TimesheetPeriod,
    TimesheetPeriodStatus,
)


@dataclass(frozen=True, slots=True)
class TimesheetPeriodAggregate:
    period_id: str
    resource_id: str
    period_start: date
    period_end: date
    status: TimesheetPeriodStatus
    submitted_at: datetime | None
    submitted_by_user_id: str | None
    submitted_by_username: str | None
    decided_at: datetime | None
    decided_by_user_id: str | None
    decided_by_username: str | None
    decision_note: str
    locked_at: datetime | None
    entry_count: int
    total_hours: float
    project_ids: tuple[str, ...]


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
        for work_allocation in self._work_allocation_repo.list_by_resource(resource_id): # work allocation could be task assignment or project role assignment
            for entry in self._time_entry_repo.list_by_work_allocation(work_allocation.id):
                if normalized_start <= entry.entry_date <= normalized_end:
                    rows.append(entry)
        rows.sort(key=lambda item: (item.entry_date, item.created_at or datetime.min.replace(tzinfo=timezone.utc)))
        return rows

    def summarize_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        period: TimesheetPeriod | None = None,
        entries: list[TimeEntry] | None = None,
    ) -> TimesheetPeriodAggregate:
        self._require_time_read_permission("summarize timesheet period")
        rows = entries if entries is not None else self.list_time_entries_for_resource_period(
            resource_id,
            period_start=period_start,
        )
        return self._build_timesheet_period_aggregate(
            resource_id=resource_id,
            period_start=period_start,
            period=period,
            entries=rows,
        )

    def _build_timesheet_period_aggregate(
        self,
        *,
        resource_id: str,
        period_start: date,
        period: TimesheetPeriod | None,
        entries: list[TimeEntry],
    ) -> TimesheetPeriodAggregate:
        normalized_start, normalized_end = self._timesheet_period_bounds(period_start)
        return TimesheetPeriodAggregate(
            period_id=period.id if period is not None else "",
            resource_id=resource_id,
            period_start=normalized_start,
            period_end=period.period_end if period is not None else normalized_end,
            status=period.status if period is not None else TimesheetPeriodStatus.OPEN,
            submitted_at=period.submitted_at if period is not None else None,
            submitted_by_user_id=(
                period.submitted_by_user_id if period is not None else None
            ),
            submitted_by_username=(
                period.submitted_by_username if period is not None else None
            ),
            decided_at=period.decided_at if period is not None else None,
            decided_by_user_id=period.decided_by_user_id if period is not None else None,
            decided_by_username=(
                period.decided_by_username if period is not None else None
            ),
            decision_note=period.decision_note if period is not None else "",
            locked_at=period.locked_at if period is not None else None,
            entry_count=len(entries),
            total_hours=self._sum_entry_hours(entries),
            project_ids=tuple(self._project_ids_for_entries(entries)),
        )


__all__ = ["TimesheetPeriodAggregate", "TimesheetQueryMixin"]
