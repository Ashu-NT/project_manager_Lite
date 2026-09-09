from __future__ import annotations

from datetime import date, datetime, timezone

from src.core.platform.common.ids import generate_id
from src.core.shared.audit import record_audit_entry
from src.core.platform.common.exceptions import ValidationError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
    WorkAllocationRepository,
    WorkOwnerRepository,
    WorkResourceRepository,
)
from src.core.platform.domain.time_management.time import TimeEntry


def _time_entry_unit_of_work(service):
    """One physical transaction for a TimeEntry mutation and its TaskAssignment-side
    side effect, wrapping TimeService's own already-shared Session. Fails loudly if
    the transactional dispatcher / post-commit bus aren't wired -- no degraded
    no-event fallback path."""
    if service._transactional_dispatcher is None or service._post_commit_bus is None:
        raise RuntimeError(
            "TimeService is missing its transactional dispatcher / post-commit bus -- "
            "TimeEntry mutations require both to be wired; there is no degraded fallback."
        )
    from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase

    return SqlAlchemyUnitOfWorkBase(
        session=service._session,
        transactional_dispatcher=service._transactional_dispatcher,
        post_commit_bus=service._post_commit_bus,
        context=DomainEventContext(correlation_id=generate_id()),
    )


def _stage_task_assignment_hours_audit_and_record_event(
    service, uow, *, work_allocation, project_id: str | None
) -> None:
    """Stages the TaskAssignment-side audit entry, precommit, in the same physical
    transaction as the TimeEntry mutation. The assignment-facing domain event (if any)
    comes from `service._build_task_assignment_hours_synced_event`, which the base
    mixin leaves a no-op -- a subclass that actually owns assignment tracking overrides
    it to produce its own fact, so this module never needs to know that vocabulary."""
    if work_allocation is None or service._tenant_context_service is None:
        return
    scope = service._tenant_context_service.require_active_scope_ids(
        operation_label="sync task assignment hours from time entries"
    )
    record_audit_entry(
        service,
        operation="update",
        entity_type="task_assignment",
        entity_id=work_allocation.id,
        module="project_management",
        organization_id=scope.organization_id,
        severity="low",
        metadata={
            "action": "assignment.hours_logged_from_time_entry",
            "hours_logged": str(getattr(work_allocation, "hours_logged", "")),
        },
        commit=False,
        fail_closed=True,
    )
    event = service._build_task_assignment_hours_synced_event(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project_id or "",
        work_allocation=work_allocation,
    )
    if event is not None:
        uow.record_event(event)


class TimesheetEntriesMixin:
    _work_allocation_repo: WorkAllocationRepository
    _work_owner_repo: WorkOwnerRepository
    _resource_repo: WorkResourceRepository
    _time_entry_repo: TimeEntryRepository | None

    def _build_task_assignment_hours_synced_event(
        self, *, tenant_id: str, organization_id: str, project_id: str, work_allocation
    ) -> object | None:
        """No assignment-event vocabulary at this layer -- override in a subclass
        that owns assignment tracking to return its own fact, or None for none."""
        return None

    def initialize_timesheet_for_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        self._require_time_manage_permission("open timesheet")
        work_allocation, work_owner, resource = self._load_work_allocation_context(work_allocation_id)
        if self._time_entry_repo is None:
            return []
        seeded_entry = None
        project_id = self._resolve_entry_project_id(work_allocation=work_allocation, work_owner=work_owner)
        try:
            seeded_entry = self._seed_legacy_hours_entry(work_allocation, work_owner, resource)
            if seeded_entry is not None:
                record_audit_entry(
                    self,
                    operation="create",
                    entity_type="time_entry",
                    entity_id=seeded_entry.id,
                    module="platform",
                    severity="low",
                    metadata={
                        "action": "time_entry.bootstrap_legacy_hours",
                        "project_id": project_id,
                        **self._build_time_entry_audit_details(
                            work_allocation=work_allocation,
                            work_owner=work_owner,
                            resource_name=resource.name if resource is not None else work_allocation.resource_id,
                            entry=seeded_entry,
                            extra={"legacy_hours_migrated": seeded_entry.hours},
                        ),
                    },
                    commit=False,
                    fail_closed=True,
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
        self._require_time_manage_permission("add time entry")
        work_allocation, work_owner, resource = self._load_work_allocation_context(work_allocation_id)
        self._require_time_project_scope(
            work_allocation=work_allocation, work_owner=work_owner, operation_label="add time entry"
        )
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
            hours=hours,
            note=note,
            author_user_id=getattr(getattr(self._user_session, "principal", None), "user_id", None),
            author_username=getattr(getattr(self._user_session, "principal", None), "username", None),
            **self._resolve_work_entry_context(
                work_allocation=work_allocation,
                work_owner=work_owner,
                resource=resource,
            ),
        )
        seeded_entry = None
        project_id = self._resolve_entry_project_id(work_allocation=work_allocation, work_owner=work_owner)
        with _time_entry_unit_of_work(self) as uow:
            seeded_entry = self._seed_legacy_hours_entry(work_allocation, work_owner, resource)
            self._time_entry_repo.add(entry)
            self._session.flush()
            updated_allocation = self._sync_work_allocation_hours_from_entries(work_allocation.id)
            _stage_task_assignment_hours_audit_and_record_event(
                self, uow, work_allocation=updated_allocation, project_id=project_id
            )
            if seeded_entry is not None:
                record_audit_entry(
                    self,
                    operation="create",
                    entity_type="time_entry",
                    entity_id=seeded_entry.id,
                    module="platform",
                    severity="low",
                    metadata={
                        "action": "time_entry.bootstrap_legacy_hours",
                        "project_id": project_id,
                        **self._build_time_entry_audit_details(
                            work_allocation=work_allocation,
                            work_owner=work_owner,
                            resource_name=resource.name if resource is not None else work_allocation.resource_id,
                            entry=seeded_entry,
                            extra={"legacy_hours_migrated": seeded_entry.hours},
                        ),
                    },
                    commit=False,
                    fail_closed=True,
                )
            record_audit_entry(
                self,
                operation="create",
                entity_type="time_entry",
                entity_id=entry.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "time_entry.add",
                    "project_id": project_id,
                    **self._build_time_entry_audit_details(
                        work_allocation=work_allocation,
                        work_owner=work_owner,
                        resource_name=resource.name if resource is not None else work_allocation.resource_id,
                        entry=entry,
                    ),
                },
                commit=False,
                fail_closed=True,
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
        self._require_time_manage_permission("update time entry")
        entry = self._require_time_entry(entry_id)
        work_allocation, work_owner, resource = self._load_work_allocation_context(entry.work_allocation_id)
        self._require_time_project_scope(
            work_allocation=work_allocation, work_owner=work_owner, operation_label="update time entry"
        )
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
            entry.hours = hours
        if note is not None:
            entry.note = note
        entry.updated_at = datetime.now(timezone.utc)
        project_id = self._resolve_entry_project_id(
            entry=entry,
            work_allocation=work_allocation,
            work_owner=work_owner,
        )
        with _time_entry_unit_of_work(self) as uow:
            self._time_entry_repo.update(entry, expected_version=expected_version)  # type: ignore[union-attr]
            self._session.flush()
            updated_allocation = self._sync_work_allocation_hours_from_entries(entry.work_allocation_id)
            _stage_task_assignment_hours_audit_and_record_event(
                self, uow, work_allocation=updated_allocation, project_id=project_id
            )
            record_audit_entry(
                self,
                operation="update",
                entity_type="time_entry",
                entity_id=entry.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "time_entry.update",
                    "project_id": project_id,
                    **self._build_time_entry_audit_details(
                        work_allocation=work_allocation,
                        work_owner=work_owner,
                        resource_name=resource.name if resource is not None else work_allocation.resource_id,
                        entry=entry,
                    ),
                },
                commit=False,
                fail_closed=True,
            )
            self._session.flush()
            uow.commit()
        return entry

    def delete_time_entry(self, entry_id: str, *, expected_version: int) -> None:
        self._require_time_manage_permission("delete time entry")
        entry = self._require_time_entry(entry_id)
        work_allocation, work_owner, resource = self._load_work_allocation_context(entry.work_allocation_id)
        self._require_time_project_scope(
            work_allocation=work_allocation, work_owner=work_owner, operation_label="delete time entry"
        )
        self._ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=entry.entry_date,
            operation_label="delete time entry",
        )
        project_id = self._resolve_entry_project_id(
            entry=entry,
            work_allocation=work_allocation,
            work_owner=work_owner,
        )
        with _time_entry_unit_of_work(self) as uow:
            self._time_entry_repo.delete(entry.id, expected_version=expected_version)  # type: ignore[union-attr]
            self._session.flush()
            updated_allocation = self._sync_work_allocation_hours_from_entries(entry.work_allocation_id)
            _stage_task_assignment_hours_audit_and_record_event(
                self, uow, work_allocation=updated_allocation, project_id=project_id
            )
            record_audit_entry(
                self,
                operation="delete",
                entity_type="time_entry",
                entity_id=entry.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "time_entry.delete",
                    "project_id": project_id,
                    **self._build_time_entry_audit_details(
                        work_allocation=work_allocation,
                        work_owner=work_owner,
                        resource_name=resource.name if resource is not None else work_allocation.resource_id,
                        entry=entry,
                    ),
                },
                commit=False,
                fail_closed=True,
            )
            self._session.flush()
            uow.commit()


__all__ = ["TimesheetEntriesMixin"]
