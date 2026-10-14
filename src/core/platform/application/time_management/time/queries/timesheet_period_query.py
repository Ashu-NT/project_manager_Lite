from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.core.platform.application.time_management.time.queries.time_entry_query import (
    TimeEntryQueryHandler,
)
from src.core.platform.application.time_management.time.timesheet_support import (
    TimesheetSupport,
)
from src.core.platform.contract.port.time_management.time.time_access_policy import (
    TimeAccessPolicy,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimesheetPeriodRepository,
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
    decision_note: str | None
    locked_at: datetime | None
    entry_count: int
    total_hours: float
    project_ids: tuple[str, ...]
    version: int = 1


class TimesheetPeriodQueryHandler:
    """Permission-checked TimesheetPeriod reads and the period aggregate projection."""

    def __init__(
        self,
        *,
        support: TimesheetSupport,
        access_policy: TimeAccessPolicy,
        entry_queries: TimeEntryQueryHandler,
        timesheet_period_repo: TimesheetPeriodRepository | None,
    ) -> None:
        self._support = support
        self._access = access_policy
        self._entry_queries = entry_queries
        self._timesheet_period_repo = timesheet_period_repo

    def get_timesheet_period(self, resource_id: str, *, period_start: date) -> TimesheetPeriod | None:
        self._access.require_read_permission("view timesheet period")
        return self._support.lookup_timesheet_period(resource_id=resource_id, period_start=period_start)

    def get_timesheet_period_record(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> TimesheetPeriod | None:
        """Return workflow state for internal task/time projections.

        PM's resource-oriented workspace owns the scoped `get_timesheet_period`
        query, so internal projections use this explicit domain-record name to
        avoid accidentally bypassing or colliding with that scoped contract.
        """
        self._access.require_read_permission("view timesheet period")
        return self._support.lookup_timesheet_period(
            resource_id=resource_id,
            period_start=period_start,
        )

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        self._access.require_read_permission("list timesheet periods")
        if self._timesheet_period_repo is None:
            return []
        return self._timesheet_period_repo.list_by_resource(resource_id)

    def summarize_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        period: TimesheetPeriod | None = None,
        entries: list[TimeEntry] | None = None,
    ) -> TimesheetPeriodAggregate:
        self._access.require_read_permission("summarize timesheet period")
        rows = entries if entries is not None else self._entry_queries.list_time_entries_for_resource_period(
            resource_id,
            period_start=period_start,
        )
        return self.build_timesheet_period_aggregate(
            resource_id=resource_id,
            period_start=period_start,
            period=period,
            entries=rows,
        )

    def build_timesheet_period_aggregate(
        self,
        *,
        resource_id: str,
        period_start: date,
        period: TimesheetPeriod | None,
        entries: list[TimeEntry],
    ) -> TimesheetPeriodAggregate:
        """Pure projection (no permission check) shared with period transitions."""
        normalized_start, normalized_end = self._support.timesheet_period_bounds(period_start)
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
            total_hours=self._support.sum_entry_hours(entries),
            project_ids=tuple(self._support.project_ids_for_entries(entries)),
            version=period.version if period is not None else 1,
        )


__all__ = ["TimesheetPeriodAggregate", "TimesheetPeriodQueryHandler"]
