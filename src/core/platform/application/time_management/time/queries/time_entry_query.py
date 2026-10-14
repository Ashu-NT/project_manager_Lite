from __future__ import annotations

from datetime import UTC, date, datetime

from src.core.platform.application.time_management.time.timesheet_support import (
    TimesheetSupport,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.port.time_management.time.time_access_policy import (
    TimeAccessPolicy,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
    WorkAllocationRepository,
)
from src.core.platform.domain.time_management.time import TimeEntry


class TimeEntryQueryHandler:
    """Permission-checked TimeEntry reads by allocation, resource period or id."""

    def __init__(
        self,
        *,
        support: TimesheetSupport,
        access_policy: TimeAccessPolicy,
        work_allocation_repo: WorkAllocationRepository,
        time_entry_repo: TimeEntryRepository | None,
    ) -> None:
        self._support = support
        self._access = access_policy
        self._work_allocation_repo = work_allocation_repo
        self._time_entry_repo = time_entry_repo

    def list_time_entries_for_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        self._access.require_read_permission("list time entries")
        work_allocation = self._work_allocation_repo.get(work_allocation_id)
        if not work_allocation:
            raise NotFoundError("Work allocation not found.", code="WORK_ALLOCATION_NOT_FOUND")
        if self._time_entry_repo is None:
            return []
        return self._time_entry_repo.list_by_work_allocation(work_allocation_id)

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return self.list_time_entries_for_work_allocation(assignment_id)

    def list_time_entries_for_work_allocations(
        self, work_allocation_ids: list[str]
    ) -> list[TimeEntry]:
        """Batched, all-time (not period-bound) lookup across several work
        allocations in one query, since a task can have several
        TaskAssignments/work allocations."""
        self._access.require_read_permission("list time entries")
        if self._time_entry_repo is None or not work_allocation_ids:
            return []
        return self._time_entry_repo.list_by_work_allocations(work_allocation_ids)

    def list_time_entries_for_work_allocation_period(
        self,
        work_allocation_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        self._access.require_read_permission("list period time entries")
        normalized_start, normalized_end = self._support.timesheet_period_bounds(period_start)
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
        self._access.require_read_permission("view time entry")
        return self._support.require_time_entry(entry_id)

    def list_time_entries_for_resource_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        self._access.require_read_permission("list resource period time entries")
        if self._time_entry_repo is None:
            return []
        normalized_start, normalized_end = self._support.timesheet_period_bounds(period_start)
        rows: list[TimeEntry] = []
        # A work allocation can be a task assignment or a project role assignment.
        for work_allocation in self._work_allocation_repo.list_by_resource(resource_id):
            for entry in self._time_entry_repo.list_by_work_allocation(work_allocation.id):
                if normalized_start <= entry.entry_date <= normalized_end:
                    rows.append(entry)
        rows.sort(key=lambda item: (item.entry_date, item.created_at or datetime.min.replace(tzinfo=UTC)))
        return rows


__all__ = ["TimeEntryQueryHandler"]
