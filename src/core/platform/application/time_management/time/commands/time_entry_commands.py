from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from src.core.platform.application.time_management.time.commands.time_entry_ledger import (
    TimeEntryLedgerRecorder,
)
from src.core.platform.application.time_management.time.timesheet_support import (
    TimesheetSupport,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.port.time_management.time.time_access_policy import (
    TimeAccessPolicy,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import TimeEntry


class TimeEntryCommandHandler:
    """TimeEntry writes: legacy-balance initialization, add, update, delete.

    Owns manage permission, module project scope and the period-editability
    rule; each mutation is one Time UoW whose staged effects (allocation hours
    sync, assignment audit/event, entry audit/activity) come from the ledger.
    """

    def __init__(
        self,
        *,
        session: Session,
        support: TimesheetSupport,
        access_policy: TimeAccessPolicy,
        ledger: TimeEntryLedgerRecorder,
        time_entry_repo: TimeEntryRepository | None,
        user_session: UserSessionContext | None,
    ) -> None:
        self._session = session
        self._support = support
        self._access = access_policy
        self._ledger = ledger
        self._time_entry_repo = time_entry_repo
        self._user_session = user_session

    def initialize_timesheet_for_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        self._access.require_manage_permission("open timesheet")
        work_allocation, work_owner, resource = self._support.load_work_allocation_context(
            work_allocation_id
        )
        if self._time_entry_repo is None:
            return []
        project_id = self._support.resolve_entry_project_id(
            work_allocation=work_allocation, work_owner=work_owner
        )
        try:
            seeded_entry = self._ledger.seed_legacy_hours_entry(work_allocation, work_owner, resource)
            if seeded_entry is not None:
                self._ledger.record_legacy_seed_audit(
                    seeded_entry,
                    work_allocation=work_allocation,
                    work_owner=work_owner,
                    resource=resource,
                    project_id=project_id,
                )
                self._session.flush()
                self._session.commit()
        except Exception:
            self._session.rollback()
            raise
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
        self._access.require_manage_permission("add time entry")
        work_allocation, work_owner, resource = self._support.load_work_allocation_context(
            work_allocation_id
        )
        self._access.require_project_scope(
            work_allocation=work_allocation, work_owner=work_owner, operation_label="add time entry"
        )
        time_entry_repo = self._time_entry_repo
        if time_entry_repo is None:
            raise ValidationError("Time entry repository is not configured.")
        self._support.ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=entry_date,
            operation_label="add time entry",
        )
        principal = getattr(self._user_session, "principal", None)
        entry = TimeEntry.create(
            work_allocation_id=work_allocation.id,
            assignment_id=self._support.legacy_assignment_id_for_work_allocation(work_allocation),
            entry_date=entry_date,
            hours=hours,
            note=note,
            author_user_id=getattr(principal, "user_id", None),
            author_username=getattr(principal, "username", None),
            **self._support.resolve_work_entry_context(
                work_allocation=work_allocation,
                work_owner=work_owner,
                resource=resource,
            ),
        )
        project_id = self._support.resolve_entry_project_id(
            work_allocation=work_allocation, work_owner=work_owner
        )
        with self._ledger.unit_of_work() as uow:
            seeded_entry = self._ledger.seed_legacy_hours_entry(work_allocation, work_owner, resource)
            time_entry_repo.add(entry)
            self._session.flush()
            self._ledger.sync_hours_and_stage_assignment_effects(
                uow, work_allocation_id=work_allocation.id, project_id=project_id
            )
            if seeded_entry is not None:
                self._ledger.record_legacy_seed_audit(
                    seeded_entry,
                    work_allocation=work_allocation,
                    work_owner=work_owner,
                    resource=resource,
                    project_id=project_id,
                )
            self._ledger.record_entry_change(
                operation="create",
                action="time_entry.add",
                entry=entry,
                work_allocation=work_allocation,
                work_owner=work_owner,
                resource=resource,
                project_id=project_id,
                activity_details={"project_id": project_id, "hours": entry.hours},
            )
            self._session.flush()
            uow.commit()
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
        expected_version: int,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ) -> TimeEntry:
        self._access.require_manage_permission("update time entry")
        entry = self._support.require_time_entry(entry_id)
        work_allocation, work_owner, resource = self._support.load_work_allocation_context(
            entry.work_allocation_id
        )
        self._access.require_project_scope(
            work_allocation=work_allocation, work_owner=work_owner, operation_label="update time entry"
        )
        self._support.ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=entry.entry_date,
            operation_label="update time entry",
        )
        target_entry_date = entry_date or entry.entry_date
        if target_entry_date != entry.entry_date:
            self._support.ensure_timesheet_period_editable(
                resource_id=work_allocation.resource_id,
                entry_date=target_entry_date,
                operation_label="move time entry",
            )
        if entry_date is not None:
            entry.entry_date = entry_date
        if hours is not None:
            entry.hours = hours
        if note is not None:
            entry.note = note
        entry.updated_at = datetime.now(UTC)
        project_id = self._support.resolve_entry_project_id(
            entry=entry,
            work_allocation=work_allocation,
            work_owner=work_owner,
        )
        time_entry_repo = self._require_time_entry_repo()
        with self._ledger.unit_of_work() as uow:
            time_entry_repo.update(entry, expected_version=expected_version)
            self._session.flush()
            self._ledger.sync_hours_and_stage_assignment_effects(
                uow, work_allocation_id=entry.work_allocation_id, project_id=project_id
            )
            self._ledger.record_entry_change(
                operation="update",
                action="time_entry.update",
                entry=entry,
                work_allocation=work_allocation,
                work_owner=work_owner,
                resource=resource,
                project_id=project_id,
                activity_details={"project_id": project_id, "hours": entry.hours},
            )
            self._session.flush()
            uow.commit()
        return entry

    def delete_time_entry(self, entry_id: str, *, expected_version: int) -> None:
        self._access.require_manage_permission("delete time entry")
        entry = self._support.require_time_entry(entry_id)
        work_allocation, work_owner, resource = self._support.load_work_allocation_context(
            entry.work_allocation_id
        )
        self._access.require_project_scope(
            work_allocation=work_allocation, work_owner=work_owner, operation_label="delete time entry"
        )
        self._support.ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=entry.entry_date,
            operation_label="delete time entry",
        )
        project_id = self._support.resolve_entry_project_id(
            entry=entry,
            work_allocation=work_allocation,
            work_owner=work_owner,
        )
        time_entry_repo = self._require_time_entry_repo()
        with self._ledger.unit_of_work() as uow:
            time_entry_repo.delete(entry.id, expected_version=expected_version)
            self._session.flush()
            self._ledger.sync_hours_and_stage_assignment_effects(
                uow, work_allocation_id=entry.work_allocation_id, project_id=project_id
            )
            self._ledger.record_entry_change(
                operation="delete",
                action="time_entry.delete",
                entry=entry,
                work_allocation=work_allocation,
                work_owner=work_owner,
                resource=resource,
                project_id=project_id,
                activity_details={"project_id": project_id},
            )
            self._session.flush()
            uow.commit()

    def _require_time_entry_repo(self) -> TimeEntryRepository:
        if self._time_entry_repo is None:
            raise ValidationError("Time entry repository is not configured.")
        return self._time_entry_repo


__all__ = ["TimeEntryCommandHandler"]
