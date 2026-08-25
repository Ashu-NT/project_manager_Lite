from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskTimeEntriesPage,
    TaskTimeEntryRow,
)
from src.core.platform.application.time_management.time import TimesheetPeriodAggregate
from src.core.platform.domain.time_management.time import TimeEntry, TimesheetPeriod


class TaskTimeEntryMixin:
    _timesheet_service: TimesheetService | None

    def _require_timesheet_service(self) -> TimesheetService:
        service = getattr(self, "_timesheet_service", None)
        if service is None:
            raise RuntimeError("Timesheet service is not configured.")
        return service

    def initialize_timesheet_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return self._require_timesheet_service().initialize_timesheet_for_assignment(assignment_id)

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return self._require_timesheet_service().list_time_entries_for_assignment(assignment_id)

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
        """Task-scoped (every TaskAssignment on this task, never just one)
        and all-time (not period-bound) Time Entries listing for Task
        Detail -> Time -> Time Entries (docs §44 Time redesign).

        Fetches the complete, authoritative entry set for this task's
        assignments in one batched repository call (`list_by_work_
        allocations`, a real SQL IN(...), never a per-assignment loop),
        then filters/sorts/paginates over that bounded, accurate dataset in
        this layer. This is deliberately NOT a dedicated SQL reader with
        pushed-down LIMIT/OFFSET (unlike the Timesheets Review Queue's
        `SqlAlchemyTimesheetReviewReader`) -- a single task's own logged
        time realistically stays small, so honest in-memory paging over
        the true total is proportionate here. If a task's entry volume
        ever grows large enough for that to stop holding, migrating to a
        dedicated reader is the natural next step (see docs §44).
        """
        assignments = self.list_assignments_for_task(task_id)
        resource_by_assignment_id = {a.id: a.resource_id for a in assignments}
        assignment_ids = list(resource_by_assignment_id)
        entries = (
            self._require_timesheet_service().list_time_entries_for_work_allocations(
                assignment_ids
            )
            if assignment_ids
            else []
        )

        rows: list[TaskTimeEntryRow] = []
        for entry in entries:
            entry_resource_id = resource_by_assignment_id.get(entry.work_allocation_id, "")
            if resource_id and entry_resource_id != resource_id:
                continue
            if date_from is not None and entry.entry_date < date_from:
                continue
            if date_to is not None and entry.entry_date > date_to:
                continue
            rows.append(
                TaskTimeEntryRow(
                    entry_id=entry.id,
                    work_allocation_id=entry.work_allocation_id,
                    resource_id=entry_resource_id,
                    entry_date=entry.entry_date,
                    hours=entry.hours,
                    note=entry.note,
                    author_username=entry.author_username,
                )
            )

        reverse = sort_direction != "asc"
        rows.sort(key=lambda row: row.entry_date, reverse=reverse)

        total = len(rows)
        normalized_page = max(page, 1)
        start = (normalized_page - 1) * page_size
        page_items = tuple(rows[start : start + page_size])

        return TaskTimeEntriesPage(
            items=page_items,
            total=total,
            page=normalized_page,
            page_size=page_size,
        )

    def list_time_entries_for_assignment_period(
        self,
        assignment_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        return self._require_timesheet_service().list_time_entries_for_assignment_period(
            assignment_id,
            period_start=period_start,
        )

    def get_time_entry(self, entry_id: str) -> TimeEntry:
        return self._require_timesheet_service().get_time_entry(entry_id)

    def add_time_entry(
        self,
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
    ) -> TimeEntry:
        return self._require_timesheet_service().add_time_entry(
            assignment_id,
            entry_date=entry_date,
            hours=hours,
            note=note,
        )

    def update_time_entry(
        self,
        entry_id: str,
        *,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ) -> TimeEntry:
        return self._require_timesheet_service().update_time_entry(
            entry_id,
            entry_date=entry_date,
            hours=hours,
            note=note,
        )

    def delete_time_entry(self, entry_id: str) -> None:
        self._require_timesheet_service().delete_time_entry(entry_id)

    def get_timesheet_period(self, resource_id: str, *, period_start: date) -> TimesheetPeriod | None:
        return self._require_timesheet_service().get_timesheet_period(resource_id, period_start=period_start)

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        return self._require_timesheet_service().list_timesheet_periods_for_resource(resource_id)

    def list_time_entries_for_resource_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        return self._require_timesheet_service().list_time_entries_for_resource_period(
            resource_id,
            period_start=period_start,
        )

    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodAggregate:
        return self._require_timesheet_service().submit_timesheet_period(
            resource_id,
            period_start=period_start,
            note=note,
        )

    def approve_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str = ""
    ) -> TimesheetPeriodAggregate:
        return self._require_timesheet_service().approve_timesheet_period(
            period_id, expected_version=expected_version, note=note
        )

    def reject_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str
    ) -> TimesheetPeriodAggregate:
        return self._require_timesheet_service().reject_timesheet_period(
            period_id, expected_version=expected_version, note=note
        )

    def lock_timesheet_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str = "",
    ) -> TimesheetPeriodAggregate:
        return self._require_timesheet_service().lock_timesheet_period(
            period_id,
            expected_version=expected_version,
            note=note,
        )

    def unlock_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str = ""
    ) -> TimesheetPeriodAggregate:
        return self._require_timesheet_service().unlock_timesheet_period(
            period_id, expected_version=expected_version, note=note
        )

    def reopen_approved_timesheet_period_for_correction(
        self, period_id: str, *, expected_version: int, note: str
    ) -> TimesheetPeriodAggregate:
        return self._require_timesheet_service().reopen_approved_timesheet_period_for_correction(
            period_id, expected_version=expected_version, note=note
        )


__all__ = ["TaskTimeEntryMixin"]
