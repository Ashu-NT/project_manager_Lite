from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.application.time_management.time.timesheet_support import (
    TimesheetSupport,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.interface.time_management.time.contracts import (
    WorkAllocationRecord,
    WorkOwnerRecord,
    WorkResourceRecord,
)
from src.core.platform.contract.port.time_management.time.work_allocation_events import (
    WorkAllocationHoursEventFactory,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
    WorkAllocationRepository,
)
from src.core.platform.contract.uow.time_management.time_unit_of_work import (
    TimeUnitOfWorkFactory,
)
from src.core.platform.domain.time_management.time import TimeEntry
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork


class TimeEntryLedgerRecorder:
    """Everything a TimeEntry mutation stages inside its one Time UoW.

    Opens the UoW on the shared Session, keeps the work allocation's
    `hours_logged` in sync (CAS-protected), seeds the legacy opening balance,
    and stages the assignment-side and TimeEntry audit/activity/event effects.
    It performs no authorization and never commits on its own.
    """

    def __init__(
        self,
        *,
        session: Session,
        support: TimesheetSupport,
        work_allocation_repo: WorkAllocationRepository,
        time_entry_repo: TimeEntryRepository | None,
        uow_factory: TimeUnitOfWorkFactory,
        transactional_dispatcher: TransactionalEventDispatcher | None,
        post_commit_bus: PostCommitEventPublisher | None,
        tenant_context_service: TenantContextService | None,
        enterprise_audit_service: Any = None,
        work_allocation_hours_event_factory: WorkAllocationHoursEventFactory | None = None,
    ) -> None:
        self._session = session
        self._support = support
        self._work_allocation_repo = work_allocation_repo
        self._time_entry_repo = time_entry_repo
        self._uow_factory = uow_factory
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus
        self._tenant_context_service = tenant_context_service
        # Read by record_audit_entry(self, ...).
        self._enterprise_audit_service = enterprise_audit_service
        self._hours_event_factory = work_allocation_hours_event_factory

    def unit_of_work(self) -> UnitOfWork:
        """One physical transaction for a TimeEntry mutation and its work-allocation
        side effect. Fails loudly if the transactional dispatcher / post-commit bus
        aren't wired -- no degraded no-event fallback path."""
        if self._transactional_dispatcher is None or self._post_commit_bus is None:
            raise RuntimeError(
                "Time entry ledger is missing its transactional dispatcher / post-commit bus -- "
                "TimeEntry mutations require both to be wired; there is no degraded fallback."
            )
        return self._uow_factory.create(
            session=self._session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=DomainEventContext(correlation_id=generate_id()),
        )

    def sync_hours_and_stage_assignment_effects(
        self, uow: UnitOfWork, *, work_allocation_id: str, project_id: str | None
    ) -> None:
        updated_allocation = self._sync_work_allocation_hours_from_entries(work_allocation_id)
        self._stage_assignment_hours_audit_and_event(
            uow, work_allocation=updated_allocation, project_id=project_id
        )

    def seed_legacy_hours_entry(
        self,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
        resource: WorkResourceRecord | None,
    ) -> TimeEntry | None:
        if self._time_entry_repo is None:
            return None
        if self._time_entry_repo.list_by_work_allocation(work_allocation.id):
            return None
        hours = float(getattr(work_allocation, "hours_logged", 0.0) or 0.0)
        if hours <= 0:
            return None
        legacy_date = self._resolve_legacy_time_entry_date(work_owner)
        self._support.ensure_timesheet_period_editable(
            resource_id=work_allocation.resource_id,
            entry_date=legacy_date,
            operation_label="seed legacy timesheet entry",
        )
        seeded_entry = TimeEntry.create(
            work_allocation_id=work_allocation.id,
            assignment_id=self._support.legacy_assignment_id_for_work_allocation(work_allocation),
            entry_date=legacy_date,
            hours=hours,
            note="Opening balance migrated from existing logged hours.",
            author_username="system",
            **self._support.resolve_work_entry_context(
                work_allocation=work_allocation,
                work_owner=work_owner,
                resource=resource,
            ),
        )
        self._time_entry_repo.add(seeded_entry)
        self._session.flush()
        self._sync_work_allocation_hours_from_entries(work_allocation.id)
        return seeded_entry

    def record_legacy_seed_audit(
        self,
        seeded_entry: TimeEntry,
        *,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
        resource: WorkResourceRecord | None,
        project_id: str | None,
    ) -> None:
        record_audit_entry(
            self,
            operation="create",
            entity_type="time_entry",
            entity_id=seeded_entry.id,
            module="platform",
            category="COMPLIANCE",
            severity="low",
            metadata={
                "action": "time_entry.bootstrap_legacy_hours",
                "project_id": project_id,
                **self._build_time_entry_audit_details(
                    work_allocation=work_allocation,
                    work_owner=work_owner,
                    resource=resource,
                    entry=seeded_entry,
                    extra={"legacy_hours_migrated": seeded_entry.hours},
                ),
            },
            commit=False,
            fail_closed=True,
        )

    def record_entry_change(
        self,
        *,
        operation: str,
        action: str,
        entry: TimeEntry,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
        resource: WorkResourceRecord | None,
        project_id: str | None,
        activity_details: dict[str, object],
    ) -> None:
        record_audit_entry(
            self,
            operation=operation,
            entity_type="time_entry",
            entity_id=entry.id,
            module="platform",
            category="COMPLIANCE",
            severity="low",
            metadata={
                "action": action,
                "project_id": project_id,
                **self._build_time_entry_audit_details(
                    work_allocation=work_allocation,
                    work_owner=work_owner,
                    resource=resource,
                    entry=entry,
                ),
            },
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=action,
            entity_type="time_entry",
            entity_id=entry.id,
            parent_entity_id=work_allocation.id,
            module="platform",
            workspace_id=project_id,
            details=activity_details,
            commit=False,
        )

    def _stage_assignment_hours_audit_and_event(
        self,
        uow: UnitOfWork,
        *,
        work_allocation: WorkAllocationRecord | None,
        project_id: str | None,
    ) -> None:
        if work_allocation is None or self._tenant_context_service is None:
            return
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="sync task assignment hours from time entries"
        )
        record_audit_entry(
            self,
            operation="update",
            entity_type="task_assignment",
            entity_id=work_allocation.id,
            module="project_management",
            organization_id=scope.organization_id,
            category="COMPLIANCE",
            severity="low",
            metadata={
                "action": "assignment.hours_logged_from_time_entry",
                "hours_logged": str(getattr(work_allocation, "hours_logged", "")),
            },
            commit=False,
            fail_closed=True,
        )
        if self._hours_event_factory is None:
            return
        event = self._hours_event_factory(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id or "",
            work_allocation=work_allocation,
        )
        if event is not None:
            uow.record_event(event)

    def _sync_work_allocation_hours_from_entries(
        self, work_allocation_id: str
    ) -> WorkAllocationRecord | None:
        """Transaction-neutral; uses the CAS-protected
        `update_hours_logged_with_version_check` instead of a blind write."""
        if self._time_entry_repo is None:
            return None
        work_allocation = self._work_allocation_repo.get(work_allocation_id)
        if not work_allocation:
            raise NotFoundError("Work allocation not found.", code="WORK_ALLOCATION_NOT_FOUND")
        entries = self._time_entry_repo.list_by_work_allocation(work_allocation_id)
        if not hasattr(work_allocation, "hours_logged"):
            self._work_allocation_repo.update(work_allocation)
            return work_allocation
        expected_version = getattr(work_allocation, "version", None)
        candidate = replace(  # type: ignore[type-var]
            work_allocation,
            hours_logged=sum(float(item.hours or 0.0) for item in entries),
        )
        if expected_version is None or not hasattr(
            self._work_allocation_repo, "update_hours_logged_with_version_check"
        ):
            self._work_allocation_repo.update(candidate)
            return candidate
        return self._work_allocation_repo.update_hours_logged_with_version_check(
            candidate, expected_version=expected_version
        )

    @staticmethod
    def _resolve_legacy_time_entry_date(work_owner: WorkOwnerRecord | None) -> date:
        actual_start = getattr(work_owner, "actual_start", None) if work_owner is not None else None
        start_date = getattr(work_owner, "start_date", None) if work_owner is not None else None
        return actual_start or start_date or date.today()  # noqa: DTZ011 - legacy local-date default preserved

    def _build_time_entry_audit_details(
        self,
        *,
        work_allocation: WorkAllocationRecord,
        work_owner: WorkOwnerRecord | None,
        resource: WorkResourceRecord | None,
        entry: TimeEntry,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        resource_name = resource.name if resource is not None else work_allocation.resource_id
        owner_label = entry.owner_label or self._support.resolve_work_owner_label(
            work_allocation, work_owner
        )
        details: dict[str, object] = {
            "work_allocation_id": entry.work_allocation_id,
            "resource_name": resource_name or work_allocation.resource_id,
            "hours": entry.hours,
            "entry_date": str(entry.entry_date),
            "owner_type": entry.owner_type,
        }
        if owner_label:
            details["owner_label"] = owner_label
            if entry.owner_type == "task_assignment":
                details["task_name"] = owner_label
        if entry.owner_id:
            details["owner_id"] = entry.owner_id
        if entry.scope_type:
            details["scope_type"] = entry.scope_type
        if entry.scope_id:
            details["scope_id"] = entry.scope_id
            if entry.scope_type == "project":
                details["project_id"] = entry.scope_id
        if entry.employee_id:
            details["employee_id"] = entry.employee_id
        if getattr(entry, "department_id", None):
            details["department_id"] = entry.department_id
        if entry.department_name:
            details["department_name"] = entry.department_name
        if getattr(entry, "site_id", None):
            details["site_id"] = entry.site_id
        if entry.site_name:
            details["site_name"] = entry.site_name
        for key, value in (extra or {}).items():
            if value is not None:
                details[key] = value
        return details


__all__ = ["TimeEntryLedgerRecorder",]
