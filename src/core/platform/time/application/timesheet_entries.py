from __future__ import annotations

from datetime import date, datetime, timezone

from src.core.platform.audit.helpers import record_audit
from core.platform.common.exceptions import ValidationError
from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.time.contracts import (
    TimeEntryRepository,
    WorkAllocationRepository,
    WorkOwnerRepository,
    WorkResourceRepository,
)
from src.core.platform.time.domain import TimeEntry


class TimesheetEntriesMixin:
    _work_allocation_repo: WorkAllocationRepository
    _work_owner_repo: WorkOwnerRepository
    _resource_repo: WorkResourceRepository
    _time_entry_repo: TimeEntryRepository | None

    def initialize_timesheet_for_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        self._require_time_manage_permission("open timesheet")
        work_allocation, work_owner, resource = self._load_work_allocation_context(work_allocation_id)
        if self._time_entry_repo is None:
            return []
        seeded_entry = None
        try:
            seeded_entry = self._seed_legacy_hours_entry(work_allocation, work_owner, resource)
            if seeded_entry is not None:
                self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        project_id = self._resolve_entry_project_id(work_allocation=work_allocation, work_owner=work_owner)
        if seeded_entry is not None:
            record_audit(
                self,
                action="time_entry.bootstrap_legacy_hours",
                entity_type="time_entry",
                entity_id=seeded_entry.id,
                project_id=project_id,
                details=self._build_time_entry_audit_details(
                    work_allocation=work_allocation,
                    work_owner=work_owner,
                    resource_name=resource.name if resource is not None else work_allocation.resource_id,
                    entry=seeded_entry,
                    extra={"legacy_hours_migrated": seeded_entry.hours},
                ),
            )
        return self._time_entry_repo.list_by_work_allocation(work_allocation_id)

    def initialize_timesheet_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return self.initialize_timesheet_for_work_allocation(assignment_id)

    def add_work_entry(
        self,
        work_allocation_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
    ) -> TimeEntry:
        self._require_time_manage_permission("add time entry")
        work_allocation, work_owner, resource = self._load_work_allocation_context(work_allocation_id)
        if self._time_entry_repo is None:
            raise ValidationError("Time entry repository is not configured.")
        self._ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=entry_date,
            operation_label="add time entry",
        )
        entry = TimeEntry.create(
            work_allocation_id=work_allocation.id,
            assignment_id=self._legacy_assignment_id_for_work_allocation(work_allocation),
            entry_date=entry_date,
            hours=self._validate_time_entry_hours(hours),
            note=(note or "").strip(),
            author_user_id=getattr(getattr(self._user_session, "principal", None), "user_id", None),
            author_username=getattr(getattr(self._user_session, "principal", None), "username", None),
            **self._resolve_work_entry_context(
                work_allocation=work_allocation,
                work_owner=work_owner,
                resource=resource,
            ),
        )
        seeded_entry = None
        try:
            seeded_entry = self._seed_legacy_hours_entry(work_allocation, work_owner, resource)
            self._time_entry_repo.add(entry)
            self._session.flush()
            self._sync_work_allocation_hours_from_entries(work_allocation.id)
            self._session.commit()
            project_id = self._resolve_entry_project_id(work_allocation=work_allocation, work_owner=work_owner)
            if seeded_entry is not None:
                record_audit(
                    self,
                    action="time_entry.bootstrap_legacy_hours",
                    entity_type="time_entry",
                    entity_id=seeded_entry.id,
                    project_id=project_id,
                    details=self._build_time_entry_audit_details(
                        work_allocation=work_allocation,
                        work_owner=work_owner,
                        resource_name=resource.name if resource is not None else work_allocation.resource_id,
                        entry=seeded_entry,
                        extra={"legacy_hours_migrated": seeded_entry.hours},
                    ),
                )
            record_audit(
                self,
                action="time_entry.add",
                entity_type="time_entry",
                entity_id=entry.id,
                project_id=project_id,
                details=self._build_time_entry_audit_details(
                    work_allocation=work_allocation,
                    work_owner=work_owner,
                    resource_name=resource.name if resource is not None else work_allocation.resource_id,
                    entry=entry,
                ),
            )
        except Exception:
            self._session.rollback()
            raise
        if project_id:
            domain_events.tasks_changed.emit(project_id)
        return entry

    def add_time_entry(
        self,
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
    ) -> TimeEntry:
        return self.add_work_entry(
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
        self._require_time_manage_permission("update time entry")
        entry = self._require_time_entry(entry_id)
        work_allocation, work_owner, resource = self._load_work_allocation_context(entry.work_allocation_id)
        self._ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=entry.entry_date,
            operation_label="update time entry",
        )
        target_entry_date = entry_date or entry.entry_date
        if target_entry_date != entry.entry_date:
            self._ensure_timesheet_period_editable(
                resource_id=work_allocation.resource_id,
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
            self._sync_work_allocation_hours_from_entries(entry.work_allocation_id)
            self._session.commit()
            project_id = self._resolve_entry_project_id(entry=entry, work_allocation=work_allocation, work_owner=work_owner)
            record_audit(
                self,
                action="time_entry.update",
                entity_type="time_entry",
                entity_id=entry.id,
                project_id=project_id,
                details=self._build_time_entry_audit_details(
                    work_allocation=work_allocation,
                    work_owner=work_owner,
                    resource_name=resource.name if resource is not None else work_allocation.resource_id,
                    entry=entry,
                ),
            )
        except Exception:
            self._session.rollback()
            raise
        if project_id:
            domain_events.tasks_changed.emit(project_id)
        return entry

    def delete_time_entry(self, entry_id: str) -> None:
        self._require_time_manage_permission("delete time entry")
        entry = self._require_time_entry(entry_id)
        work_allocation, work_owner, resource = self._load_work_allocation_context(entry.work_allocation_id)
        self._ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=entry.entry_date,
            operation_label="delete time entry",
        )
        try:
            self._time_entry_repo.delete(entry.id)  # type: ignore[union-attr]
            self._session.flush()
            self._sync_work_allocation_hours_from_entries(entry.work_allocation_id)
            self._session.commit()
            project_id = self._resolve_entry_project_id(entry=entry, work_allocation=work_allocation, work_owner=work_owner)
            record_audit(
                self,
                action="time_entry.delete",
                entity_type="time_entry",
                entity_id=entry.id,
                project_id=project_id,
                details=self._build_time_entry_audit_details(
                    work_allocation=work_allocation,
                    work_owner=work_owner,
                    resource_name=resource.name if resource is not None else work_allocation.resource_id,
                    entry=entry,
                ),
            )
        except Exception:
            self._session.rollback()
            raise
        if project_id:
            domain_events.tasks_changed.emit(project_id)


__all__ = ["TimesheetEntriesMixin"]
