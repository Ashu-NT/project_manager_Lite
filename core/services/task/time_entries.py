from __future__ import annotations

from datetime import date, datetime, timezone

from core.events.domain_events import domain_events
from core.exceptions import NotFoundError, ValidationError
from core.domain.task import Task
from core.interfaces import AssignmentRepository, ResourceRepository, TaskRepository, TimeEntryRepository
from core.models import TaskAssignment, TimeEntry
from core.services.audit.helpers import record_audit
from core.services.auth.authorization import require_permission


class TaskTimeEntryMixin:
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
        seeded_entry = TimeEntry.create(
            assignment_id=assignment.id,
            entry_date=self._resolve_legacy_time_entry_date(task),
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


__all__ = ["TaskTimeEntryMixin"]
