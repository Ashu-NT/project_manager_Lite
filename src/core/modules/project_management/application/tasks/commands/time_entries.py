from __future__ import annotations

from datetime import date

from src.core.platform.time.domain import TimeEntry, TimesheetPeriod
from src.core.modules.project_management.application.resources import TimesheetService


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
    ) -> TimesheetPeriod:
        return self._require_timesheet_service().submit_timesheet_period(
            resource_id,
            period_start=period_start,
            note=note,
        )

    def approve_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        return self._require_timesheet_service().approve_timesheet_period(period_id, note=note)

    def reject_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        return self._require_timesheet_service().reject_timesheet_period(period_id, note=note)

    def lock_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        return self._require_timesheet_service().lock_timesheet_period(
            resource_id,
            period_start=period_start,
            note=note,
        )

    def unlock_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        return self._require_timesheet_service().unlock_timesheet_period(period_id, note=note)


__all__ = ["TaskTimeEntryMixin"]
