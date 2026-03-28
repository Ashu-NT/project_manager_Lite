from __future__ import annotations

from datetime import date, datetime, timezone

from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError
from core.modules.project_management.interfaces import AssignmentRepository
from core.platform.time.domain import TimeEntry, TimesheetPeriod
from core.platform.time.interfaces import TimeEntryRepository, TimesheetPeriodRepository


class TimesheetQueryMixin:
    _assignment_repo: AssignmentRepository
    _time_entry_repo: TimeEntryRepository | None
    _timesheet_period_repo: TimesheetPeriodRepository | None

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        require_permission(self._user_session, "task.read", operation_label="list time entries")
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        if self._time_entry_repo is None:
            return []
        return self._time_entry_repo.list_by_assignment(assignment_id)

    def list_time_entries_for_assignment_period(
        self,
        assignment_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        require_permission(self._user_session, "task.read", operation_label="list period time entries")
        normalized_start, normalized_end = self._timesheet_period_bounds(period_start)
        return [
            entry
            for entry in self.list_time_entries_for_assignment(assignment_id)
            if normalized_start <= entry.entry_date <= normalized_end
        ]

    def get_time_entry(self, entry_id: str) -> TimeEntry:
        require_permission(self._user_session, "task.read", operation_label="view time entry")
        return self._require_time_entry(entry_id)

    def get_timesheet_period(self, resource_id: str, *, period_start: date) -> TimesheetPeriod | None:
        require_permission(self._user_session, "task.read", operation_label="view timesheet period")
        if self._timesheet_period_repo is None:
            return None
        normalized_start, _ = self._timesheet_period_bounds(period_start)
        return self._timesheet_period_repo.get_by_resource_period(resource_id, normalized_start)

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        require_permission(self._user_session, "task.read", operation_label="list timesheet periods")
        if self._timesheet_period_repo is None:
            return []
        return self._timesheet_period_repo.list_by_resource(resource_id)

    def list_time_entries_for_resource_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        require_permission(self._user_session, "task.read", operation_label="list resource period time entries")
        if self._time_entry_repo is None:
            return []
        normalized_start, normalized_end = self._timesheet_period_bounds(period_start)
        rows: list[TimeEntry] = []
        for assignment in self._assignment_repo.list_by_resource(resource_id):
            for entry in self._time_entry_repo.list_by_assignment(assignment.id):
                if normalized_start <= entry.entry_date <= normalized_end:
                    rows.append(entry)
        rows.sort(key=lambda item: (item.entry_date, item.created_at or datetime.min.replace(tzinfo=timezone.utc)))
        return rows


__all__ = ["TimesheetQueryMixin"]
