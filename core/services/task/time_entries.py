from __future__ import annotations

import calendar
from datetime import date, datetime, timezone

from core.events.domain_events import domain_events
from core.exceptions import NotFoundError, ValidationError
from core.domain.task import Task
from core.interfaces import (
    AssignmentRepository,
    ResourceRepository,
    TaskRepository,
    TimeEntryRepository,
    TimesheetPeriodRepository,
)
from core.models import TaskAssignment, TimeEntry, TimesheetPeriod, TimesheetPeriodStatus
from core.services.audit.helpers import record_audit
from core.services.auth.authorization import require_permission


class TaskTimeEntryMixin:
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _task_repo: TaskRepository
    _time_entry_repo: TimeEntryRepository | None
    _timesheet_period_repo: TimesheetPeriodRepository | None

    def initialize_timesheet_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        require_permission(self._user_session, "task.manage", operation_label="open timesheet")
        assignment, task, resource = self._load_assignment_context(assignment_id)
        if self._time_entry_repo is None:
            return []
        seeded_entry = None
        try:
            seeded_entry = self._seed_legacy_hours_entry(assignment, task)
            if seeded_entry is not None:
                self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        if seeded_entry is not None:
            record_audit(
                self,
                action="time_entry.bootstrap_legacy_hours",
                entity_type="time_entry",
                entity_id=seeded_entry.id,
                project_id=task.project_id,
                details=self._build_time_entry_audit_details(
                    assignment=assignment,
                    task=task,
                    resource_name=resource.name if resource is not None else assignment.resource_id,
                    entry=seeded_entry,
                    extra={"legacy_hours_migrated": seeded_entry.hours},
                ),
            )
        return self._time_entry_repo.list_by_assignment(assignment_id)

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        if self._time_entry_repo is None:
            return []
        return self._time_entry_repo.list_by_assignment(assignment_id)

    def add_time_entry(
        self,
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
    ) -> TimeEntry:
        require_permission(self._user_session, "task.manage", operation_label="add time entry")
        assignment, task, resource = self._load_assignment_context(assignment_id)
        if self._time_entry_repo is None:
            raise ValidationError("Time entry repository is not configured.")
        self._ensure_timesheet_period_editable(
            resource_id=assignment.resource_id,
            entry_date=entry_date,
            operation_label="add time entry",
        )
        entry = TimeEntry.create(
            assignment_id=assignment.id,
            entry_date=entry_date,
            hours=self._validate_time_entry_hours(hours),
            note=(note or "").strip(),
            author_user_id=getattr(getattr(self._user_session, "principal", None), "user_id", None),
            author_username=getattr(getattr(self._user_session, "principal", None), "username", None),
        )
        seeded_entry = None
        try:
            seeded_entry = self._seed_legacy_hours_entry(assignment, task)
            self._time_entry_repo.add(entry)
            self._session.flush()
            self._sync_assignment_hours_from_entries(assignment.id)
            self._session.commit()
            if seeded_entry is not None:
                record_audit(
                    self,
                    action="time_entry.bootstrap_legacy_hours",
                    entity_type="time_entry",
                    entity_id=seeded_entry.id,
                    project_id=task.project_id,
                    details=self._build_time_entry_audit_details(
                        assignment=assignment,
                        task=task,
                        resource_name=resource.name if resource is not None else assignment.resource_id,
                        entry=seeded_entry,
                        extra={"legacy_hours_migrated": seeded_entry.hours},
                    ),
                )
            record_audit(
                self,
                action="time_entry.add",
                entity_type="time_entry",
                entity_id=entry.id,
                project_id=task.project_id,
                details=self._build_time_entry_audit_details(
                    assignment=assignment,
                    task=task,
                    resource_name=resource.name if resource is not None else assignment.resource_id,
                    entry=entry,
                ),
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.tasks_changed.emit(task.project_id)
        return entry

    def update_time_entry(
        self,
        entry_id: str,
        *,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ) -> TimeEntry:
        require_permission(self._user_session, "task.manage", operation_label="update time entry")
        entry = self._require_time_entry(entry_id)
        assignment, task, resource = self._load_assignment_context(entry.assignment_id)
        self._ensure_timesheet_period_editable(
            resource_id=assignment.resource_id,
            entry_date=entry.entry_date,
            operation_label="update time entry",
        )
        target_entry_date = entry_date or entry.entry_date
        if target_entry_date != entry.entry_date:
            self._ensure_timesheet_period_editable(
                resource_id=assignment.resource_id,
                entry_date=target_entry_date,
                operation_label="move time entry",
            )
        if entry_date is not None:
            entry.entry_date = entry_date
        if hours is not None:
            entry.hours = self._validate_time_entry_hours(hours)
        if note is not None:
            entry.note = note.strip()
        entry.updated_at = datetime.now(timezone.utc)
        try:
            self._time_entry_repo.update(entry)  # type: ignore[union-attr]
            self._session.flush()
            self._sync_assignment_hours_from_entries(entry.assignment_id)
            self._session.commit()
            record_audit(
                self,
                action="time_entry.update",
                entity_type="time_entry",
                entity_id=entry.id,
                project_id=task.project_id,
                details=self._build_time_entry_audit_details(
                    assignment=assignment,
                    task=task,
                    resource_name=resource.name if resource is not None else assignment.resource_id,
                    entry=entry,
                ),
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.tasks_changed.emit(task.project_id)
        return entry

    def delete_time_entry(self, entry_id: str) -> None:
        require_permission(self._user_session, "task.manage", operation_label="delete time entry")
        entry = self._require_time_entry(entry_id)
        assignment, task, resource = self._load_assignment_context(entry.assignment_id)
        self._ensure_timesheet_period_editable(
            resource_id=assignment.resource_id,
            entry_date=entry.entry_date,
            operation_label="delete time entry",
        )
        try:
            self._time_entry_repo.delete(entry.id)  # type: ignore[union-attr]
            self._session.flush()
            self._sync_assignment_hours_from_entries(entry.assignment_id)
            self._session.commit()
            record_audit(
                self,
                action="time_entry.delete",
                entity_type="time_entry",
                entity_id=entry.id,
                project_id=task.project_id,
                details=self._build_time_entry_audit_details(
                    assignment=assignment,
                    task=task,
                    resource_name=resource.name if resource is not None else assignment.resource_id,
                    entry=entry,
                ),
            )
        except Exception:
            self._session.rollback()
            raise
        domain_events.tasks_changed.emit(task.project_id)

    def get_timesheet_period(self, resource_id: str, *, period_start: date) -> TimesheetPeriod | None:
        if self._timesheet_period_repo is None:
            return None
        normalized_start, _ = self._timesheet_period_bounds(period_start)
        return self._timesheet_period_repo.get_by_resource_period(resource_id, normalized_start)

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        if self._timesheet_period_repo is None:
            return []
        return self._timesheet_period_repo.list_by_resource(resource_id)

    def list_time_entries_for_resource_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
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

    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        require_permission(self._user_session, "task.manage", operation_label="submit timesheet period")
        entries = self.list_time_entries_for_resource_period(resource_id, period_start=period_start)
        if not entries:
            raise ValidationError("Cannot submit an empty timesheet period.")
        period = self._get_or_create_timesheet_period(resource_id=resource_id, period_start=period_start)
        if period.status in {TimesheetPeriodStatus.SUBMITTED, TimesheetPeriodStatus.APPROVED, TimesheetPeriodStatus.LOCKED}:
            raise ValidationError(
                f"Timesheet period {period.period_start.isoformat()} is already {period.status.value.lower()}."
            )
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.SUBMITTED
        period.submitted_at = datetime.now(timezone.utc)
        period.submitted_by_user_id = getattr(principal, "user_id", None)
        period.submitted_by_username = getattr(principal, "username", None)
        period.decided_at = None
        period.decided_by_user_id = None
        period.decided_by_username = None
        period.decision_note = (note or "").strip() or None
        period.locked_at = None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        record_audit(
            self,
            action="timesheet_period.submit",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(period=period, entry_count=len(entries), total_hours=self._sum_entry_hours(entries)),
        )
        return period

    def approve_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        require_permission(self._user_session, "approval.decide", operation_label="approve timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be approved.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.APPROVED
        period.decided_at = datetime.now(timezone.utc)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = (note or "").strip() or None
        period.locked_at = period.decided_at
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        record_audit(
            self,
            action="timesheet_period.approve",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(period=period, entry_count=len(entries), total_hours=self._sum_entry_hours(entries)),
        )
        return period

    def reject_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        require_permission(self._user_session, "approval.decide", operation_label="reject timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be rejected.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.REJECTED
        period.decided_at = datetime.now(timezone.utc)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = (note or "").strip() or None
        period.locked_at = None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        record_audit(
            self,
            action="timesheet_period.reject",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(period=period, entry_count=len(entries), total_hours=self._sum_entry_hours(entries)),
        )
        return period

    def lock_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        require_permission(self._user_session, "settings.manage", operation_label="lock timesheet period")
        period = self._get_or_create_timesheet_period(resource_id=resource_id, period_start=period_start)
        if period.status == TimesheetPeriodStatus.APPROVED:
            raise ValidationError("Approved timesheet periods are already locked.")
        period.status = TimesheetPeriodStatus.LOCKED
        period.locked_at = datetime.now(timezone.utc)
        period.decision_note = (note or "").strip() or None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        entries = self.list_time_entries_for_resource_period(resource_id, period_start=period.period_start)
        record_audit(
            self,
            action="timesheet_period.lock",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(
                period=period,
                entry_count=len(entries),
                total_hours=self._sum_entry_hours(entries),
            ),
        )
        return period

    def unlock_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        require_permission(self._user_session, "settings.manage", operation_label="unlock timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.LOCKED:
            raise ValidationError("Only explicitly locked timesheet periods can be unlocked.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        period.status = TimesheetPeriodStatus.OPEN
        period.locked_at = None
        period.decision_note = (note or "").strip() or None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        record_audit(
            self,
            action="timesheet_period.unlock",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(period=period, entry_count=len(entries), total_hours=self._sum_entry_hours(entries)),
        )
        return period

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

    def _sync_assignment_hours_from_entries(self, assignment_id: str) -> None:
        if self._time_entry_repo is None:
            return
        assignment = self._assignment_repo.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        entries = self._time_entry_repo.list_by_assignment(assignment_id)
        assignment.hours_logged = sum(float(item.hours or 0.0) for item in entries)
        self._assignment_repo.update(assignment)

    def _seed_legacy_hours_entry(self, assignment: TaskAssignment, task: Task) -> TimeEntry | None:
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
        )
        self._time_entry_repo.add(seeded_entry)
        self._session.flush()
        self._sync_assignment_hours_from_entries(assignment.id)
        return seeded_entry

    @staticmethod
    def _resolve_legacy_time_entry_date(task: Task) -> date:
        return task.actual_start or task.start_date or date.today()

    @staticmethod
    def _build_time_entry_audit_details(
        *,
        assignment: TaskAssignment,
        task: Task,
        resource_name: str,
        entry: TimeEntry,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        details: dict[str, object] = {
            "task_name": task.name,
            "resource_name": resource_name or assignment.resource_id,
            "hours": entry.hours,
            "entry_date": str(entry.entry_date),
        }
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
    ) -> dict[str, object]:
        resource = self._resource_repo.get(period.resource_id)
        return {
            "resource_name": resource.name if resource is not None else period.resource_id,
            "period_start": str(period.period_start),
            "period_end": str(period.period_end),
            "status": period.status.value,
            "entry_count": entry_count,
            "total_hours": total_hours,
        }


__all__ = ["TaskTimeEntryMixin"]
