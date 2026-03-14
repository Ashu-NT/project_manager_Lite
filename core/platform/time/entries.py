from __future__ import annotations

from datetime import date, datetime, timezone

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ValidationError
from core.platform.common.interfaces import AssignmentRepository, ResourceRepository, TaskRepository
from core.platform.notifications.domain_events import domain_events
from core.platform.time.domain import TimeEntry
from core.platform.time.interfaces import TimeEntryRepository


class TimesheetEntriesMixin:
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _task_repo: TaskRepository
    _time_entry_repo: TimeEntryRepository | None

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
            **self._resolve_work_entry_context(assignment=assignment, resource=resource),
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


__all__ = ["TimesheetEntriesMixin"]
