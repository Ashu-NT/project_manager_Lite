from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from core.platform.auth.authorization import require_any_permission
from core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


@dataclass(frozen=True, slots=True)
class TimesheetReviewQueueItem:
    period_id: str
    resource_id: str
    resource_name: str
    period_start: date
    period_end: date
    status: TimesheetPeriodStatus
    submitted_at: datetime | None
    submitted_by_username: str | None
    decided_at: datetime | None
    decided_by_username: str | None
    decision_note: str | None
    entry_count: int
    total_hours: float
    project_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TimesheetReviewEntry:
    entry_id: str
    entry_date: date
    hours: float
    note: str
    author_username: str | None
    task_id: str | None
    task_name: str
    project_id: str | None


@dataclass(frozen=True, slots=True)
class TimesheetReviewDetail:
    summary: TimesheetReviewQueueItem
    entries: tuple[TimesheetReviewEntry, ...]


class TimesheetReviewMixin:
    def list_timesheet_review_queue(
        self,
        *,
        status: TimesheetPeriodStatus | None = TimesheetPeriodStatus.SUBMITTED,
        limit: int = 200,
    ) -> list[TimesheetReviewQueueItem]:
        require_any_permission(
            self._user_session,
            ("timesheet.approve", "timesheet.lock"),
            operation_label="view timesheet review queue",
        )
        if self._timesheet_period_repo is None:
            return []
        periods = self._timesheet_period_repo.list_all(status=status, limit=limit)
        return [self._build_review_queue_item(period) for period in periods]

    def get_timesheet_review_detail(self, period_id: str) -> TimesheetReviewDetail:
        require_any_permission(
            self._user_session,
            ("timesheet.approve", "timesheet.lock"),
            operation_label="view timesheet review detail",
        )
        period = self._require_timesheet_period(period_id)
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        return TimesheetReviewDetail(
            summary=self._build_review_queue_item(period, entries=entries),
            entries=tuple(self._build_review_entries(entries)),
        )

    def _build_review_queue_item(
        self,
        period: TimesheetPeriod,
        *,
        entries: list[TimeEntry] | None = None,
    ) -> TimesheetReviewQueueItem:
        rows = entries if entries is not None else self.list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        resource = self._resource_repo.get(period.resource_id)
        return TimesheetReviewQueueItem(
            period_id=period.id,
            resource_id=period.resource_id,
            resource_name=resource.name if resource is not None else period.resource_id,
            period_start=period.period_start,
            period_end=period.period_end,
            status=period.status,
            submitted_at=period.submitted_at,
            submitted_by_username=period.submitted_by_username,
            decided_at=period.decided_at,
            decided_by_username=period.decided_by_username,
            decision_note=period.decision_note,
            entry_count=len(rows),
            total_hours=self._sum_entry_hours(rows),
            project_ids=tuple(self._project_ids_for_entries(rows)),
        )

    def _build_review_entries(self, entries: list[TimeEntry]) -> list[TimesheetReviewEntry]:
        rows: list[TimesheetReviewEntry] = []
        for entry in entries:
            assignment = self._assignment_repo.get(entry.assignment_id)
            task = self._task_repo.get(assignment.task_id) if assignment is not None else None
            rows.append(
                TimesheetReviewEntry(
                    entry_id=entry.id,
                    entry_date=entry.entry_date,
                    hours=float(entry.hours or 0.0),
                    note=entry.note or "",
                    author_username=entry.author_username,
                    task_id=task.id if task is not None else None,
                    task_name=task.name if task is not None else (assignment.task_id if assignment is not None else ""),
                    project_id=task.project_id if task is not None else None,
                )
            )
        rows.sort(key=lambda item: (item.entry_date, item.task_name.lower(), item.entry_id))
        return rows


__all__ = [
    "TimesheetReviewDetail",
    "TimesheetReviewEntry",
    "TimesheetReviewMixin",
    "TimesheetReviewQueueItem",
]
