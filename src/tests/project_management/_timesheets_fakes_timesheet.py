"""Shared fake timesheet service implementation for timesheet desktop API tests."""
from datetime import date, datetime
from types import SimpleNamespace

from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.platform.domain.time_management.time import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus
from src.core.platform.application.time_management.time import TimesheetPeriodAggregate
from src.tests.project_management._timesheets_fakes_services import (
    _FakeResourceService,
    _FakeTaskService,
    _test_period_end,
)


class _FakeTimesheetService:
    def __init__(
        self,
        *,
        task_service: _FakeTaskService,
        resource_service: _FakeResourceService,
    ) -> None:
        self._task_service = task_service
        self._resource_service = resource_service
        self._entries: dict[str, TimeEntry] = {}
        self._periods: dict[tuple[str, date], TimesheetPeriod] = {}
        self.resource_period_read_count = 0

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return [e for e in self._entries.values() if e.assignment_id == assignment_id]

    def list_time_entries_for_assignment_period(
        self,
        assignment_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        return [
            e for e in self.list_time_entries_for_assignment(assignment_id)
            if e.entry_date.year == period_start.year and e.entry_date.month == period_start.month
        ]

    def list_time_entries_for_resource_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        self.resource_period_read_count += 1
        return [
            e for e in self._entries.values()
            if self._resource_id_for_entry(e) == resource_id
            and e.entry_date.year == period_start.year
            and e.entry_date.month == period_start.month
        ]

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        return [
            period
            for (current_resource_id, _), period in self._periods.items()
            if current_resource_id == resource_id
        ]

    def get_timesheet_period(self, resource_id: str, *, period_start: date) -> TimesheetPeriod:
        return self._ensure_period(resource_id, period_start)

    def add_time_entry(
        self,
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
    ) -> TimeEntry:
        assignment = self._task_service.get_assignment(assignment_id)
        task = self._task_service.get_task(assignment.task_id) if assignment is not None else None
        entry = TimeEntry(
            id=f"entry-{len(self._entries) + 1}",
            work_allocation_id=assignment_id,
            assignment_id=assignment_id,
            entry_date=entry_date,
            hours=float(hours),
            note=note,
            author_username="alex",
            owner_type="task_assignment",
            owner_id=getattr(task, "id", None),
            owner_label=getattr(task, "name", assignment_id),
            scope_type="project",
            scope_id=getattr(task, "project_id", None),
        )
        self._entries[entry.id] = entry
        self._ensure_period(assignment.resource_id, entry_date.replace(day=1))
        return entry

    def update_time_entry(
        self,
        entry_id: str,
        *,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ) -> TimeEntry:
        entry = self._entries[entry_id]
        if entry_date is not None:
            entry.entry_date = entry_date
        if hours is not None:
            entry.hours = float(hours)
        if note is not None:
            entry.note = note
        return entry

    def delete_time_entry(self, entry_id: str) -> None:
        del self._entries[entry_id]

    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodAggregate:
        period = self._ensure_period(resource_id, period_start)
        period.status = TimesheetPeriodStatus.SUBMITTED
        period.submitted_at = datetime(2026, 5, 4, 17, 0)
        period.submitted_by_username = "alex"
        period.decision_note = note
        return self._aggregate(period)

    def approve_timesheet_period(
        self, period_id: str, *, note: str = ""
    ) -> TimesheetPeriodAggregate:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.APPROVED
        period.decided_at = datetime(2026, 5, 5, 9, 0)
        period.decided_by_username = "jamie"
        period.decision_note = note
        return self._aggregate(period)

    def reject_timesheet_period(
        self, period_id: str, *, note: str = ""
    ) -> TimesheetPeriodAggregate:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.REJECTED
        period.decided_at = datetime(2026, 5, 5, 9, 0)
        period.decided_by_username = "jamie"
        period.decision_note = note
        return self._aggregate(period)

    def lock_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodAggregate:
        period = self._ensure_period(resource_id, period_start)
        period.status = TimesheetPeriodStatus.LOCKED
        period.locked_at = datetime(2026, 5, 6, 18, 0)
        period.decision_note = note
        return self._aggregate(period)

    def unlock_timesheet_period(
        self, period_id: str, *, note: str = ""
    ) -> TimesheetPeriodAggregate:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.OPEN
        period.decision_note = note
        period.locked_at = None
        return self._aggregate(period)

    def summarize_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        period: TimesheetPeriod | None = None,
        entries: list[TimeEntry] | None = None,
    ) -> TimesheetPeriodAggregate:
        current_period = period or self._periods.get((resource_id, period_start))
        rows = entries if entries is not None else self.list_time_entries_for_resource_period(
            resource_id,
            period_start=period_start,
        )
        return self._aggregate_from_rows(
            resource_id=resource_id,
            period_start=period_start,
            period=current_period,
            entries=rows,
        )

    def list_timesheet_review_queue(
        self,
        *,
        status: TimesheetPeriodStatus | None = TimesheetPeriodStatus.SUBMITTED,
        limit: int = 200,
    ) -> list[SimpleNamespace]:
        rows: list[SimpleNamespace] = []
        for period in self._periods.values():
            if status is not None and period.status != status:
                continue
            rows.append(self._build_review_summary(period))
        return rows[:limit]

    def query_review_queue_page(
        self,
        *,
        status=TimesheetPeriodStatus.SUBMITTED,
        page=1,
        page_size=25,
    ) -> SimpleNamespace:
        rows = self.list_timesheet_review_queue(status=status, limit=10000)
        offset = (page - 1) * page_size
        return SimpleNamespace(
            items=tuple(rows[offset:offset + page_size]),
            total=len(rows),
            page=page,
            page_size=page_size,
        )

    def get_timesheet_review_detail(self, period_id: str) -> SimpleNamespace:
        period = self._period_by_id(period_id)
        summary = self._build_review_summary(period)
        entries = self.list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        review_entries = []
        for entry in entries:
            assignment = self._task_service.get_assignment(entry.assignment_id or "")
            task = self._task_service.get_task(assignment.task_id) if assignment is not None else None
            review_entries.append(
                SimpleNamespace(
                    entry_id=entry.id,
                    entry_date=entry.entry_date,
                    hours=float(entry.hours or 0.0),
                    note=entry.note or "",
                    author_username=entry.author_username,
                    task_name=getattr(task, "name", entry.owner_label or ""),
                    project_id=getattr(task, "project_id", None),
                )
            )
        return SimpleNamespace(summary=summary, entries=tuple(review_entries))

    def _build_review_summary(self, period: TimesheetPeriod) -> SimpleNamespace:
        entries = self.list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        resource = self._resource_service.get_resource(period.resource_id)
        project_ids = sorted(
            {
                entry.scope_id
                for entry in entries
                if getattr(entry, "scope_type", None) == "project" and getattr(entry, "scope_id", None)
            }
        )
        return SimpleNamespace(
            period_id=period.id,
            resource_id=period.resource_id,
            resource_name=getattr(resource, "name", period.resource_id),
            period_start=period.period_start,
            period_end=period.period_end,
            status=period.status,
            submitted_at=period.submitted_at,
            submitted_by_username=period.submitted_by_username,
            decided_at=period.decided_at,
            decided_by_username=period.decided_by_username,
            decision_note=period.decision_note,
            entry_count=len(entries),
            total_hours=sum(float(entry.hours or 0.0) for entry in entries),
            project_ids=tuple(project_ids),
        )

    def _ensure_period(self, resource_id: str, period_start: date) -> TimesheetPeriod:
        key = (resource_id, period_start)
        if key not in self._periods:
            self._periods[key] = TimesheetPeriod(
                id=f"period-{len(self._periods) + 1}",
                resource_id=resource_id,
                period_start=period_start,
                period_end=_test_period_end(period_start),
            )
        return self._periods[key]

    def _aggregate(self, period: TimesheetPeriod) -> TimesheetPeriodAggregate:
        entries = self.list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        return self._aggregate_from_rows(
            resource_id=period.resource_id,
            period_start=period.period_start,
            period=period,
            entries=entries,
        )

    @staticmethod
    def _aggregate_from_rows(
        *,
        resource_id: str,
        period_start: date,
        period: TimesheetPeriod | None,
        entries: list[TimeEntry],
    ) -> TimesheetPeriodAggregate:
        project_ids = tuple(
            sorted(
                {
                    entry.scope_id
                    for entry in entries
                    if entry.scope_type == "project" and entry.scope_id
                }
            )
        )
        return TimesheetPeriodAggregate(
            period_id=period.id if period else "",
            resource_id=resource_id,
            period_start=period_start,
            period_end=period.period_end if period else _test_period_end(period_start),
            status=period.status if period else TimesheetPeriodStatus.OPEN,
            submitted_at=period.submitted_at if period else None,
            submitted_by_user_id=period.submitted_by_user_id if period else None,
            submitted_by_username=period.submitted_by_username if period else None,
            decided_at=period.decided_at if period else None,
            decided_by_user_id=period.decided_by_user_id if period else None,
            decided_by_username=period.decided_by_username if period else None,
            decision_note=period.decision_note if period else "",
            locked_at=period.locked_at if period else None,
            entry_count=len(entries),
            total_hours=sum(float(entry.hours or 0.0) for entry in entries),
            project_ids=project_ids,
        )

    def _period_by_id(self, period_id: str) -> TimesheetPeriod:
        for period in self._periods.values():
            if period.id == period_id:
                return period
        raise KeyError(period_id)

    def _resource_id_for_entry(self, entry: TimeEntry) -> str | None:
        assignment = self._task_service.get_assignment(entry.assignment_id or "")
        return assignment.resource_id if assignment is not None else None
