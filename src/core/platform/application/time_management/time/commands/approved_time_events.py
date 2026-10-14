from __future__ import annotations

from typing import Any

from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.application.time_management.time.timesheet_support import (
    TimesheetSupport,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.time_management.time.contracts import (
    WorkAllocationRepository,
)
from src.core.platform.domain.finance import DecimalQuantity, DecimalQuantityPayload
from src.core.platform.domain.time_management.time import TimeEntry, TimesheetPeriod
from src.core.platform.integration import (
    APPROVED_TIME_ENTRY_EVENT_TYPE,
    ApprovedTimeEntryEventPayload,
    IntegrationEventEnvelope,
)
from src.core.platform.integration.canonical_json import canonical_json_sha256


class ApprovedTimeEventPublisher:
    """Stages Approved Time integration events in the caller's transaction.

    Content-hash dedupe against the latest outbox row per TimeEntry keeps
    re-approval one-effect; a changed entry emits a correction revision.
    """

    def __init__(
        self,
        *,
        outbox_service: IntegrationOutboxService | None,
        tenant_context_service: TenantContextService | None,
        work_allocation_repo: WorkAllocationRepository,
        support: TimesheetSupport,
    ) -> None:
        self._outbox_service = outbox_service
        self._tenant_context_service = tenant_context_service
        self._work_allocation_repo = work_allocation_repo
        self._support = support

    def enqueue_approved_time_events(
        self, *, period: TimesheetPeriod, entries: list[TimeEntry]
    ) -> int:
        outbox = self._outbox_service
        if outbox is None:
            return 0
        if self._tenant_context_service is None:
            raise RuntimeError("Approved Time publishing requires the tenant context service.")
        context = self._tenant_context_service.require_active_scope_ids(
            operation_label="publish approved time"
        )
        approved_at = period.decided_at
        if approved_at is None:
            raise BusinessRuleError(
                "Approved timesheet period is missing its decision timestamp.",
                code="APPROVED_TIME_TIMESTAMP_REQUIRED",
            )
        # Resolve project_id for every entry up front, then batch-fetch every
        # distinct work allocation ONE time instead of once per entry.
        resolved_entries: list[tuple[TimeEntry, str]] = []
        work_allocation_ids: set[str] = set()
        for entry in entries:
            project_id = self._support.resolve_entry_project_id(entry=entry)
            if not project_id:
                continue
            resolved_entries.append((entry, project_id))
            if entry.work_allocation_id:
                work_allocation_ids.add(entry.work_allocation_id)
        allocations_by_id = {
            allocation.id: allocation
            for allocation in self._work_allocation_repo.list_by_ids(sorted(work_allocation_ids))
        }

        emitted = 0
        for entry, project_id in resolved_entries:
            allocation = allocations_by_id.get(entry.work_allocation_id)
            task_id = getattr(allocation, "task_id", None) if allocation is not None else None
            if entry.organization_id and entry.organization_id != context.organization_id:
                raise BusinessRuleError(
                    "Approved Time entry is outside the active organization.",
                    code="APPROVED_TIME_SCOPE_MISMATCH",
                )
            facts: dict[str, Any] = {
                "timesheet_period_id": period.id,
                "time_entry_id": entry.id,
                "work_allocation_id": entry.work_allocation_id,
                "resource_id": period.resource_id,
                "project_id": project_id,
                "organization_id": context.organization_id,
                "employee_id": entry.employee_id,
                "assignment_id": entry.assignment_id,
                "task_id": task_id,
                "work_date": entry.entry_date.isoformat(),
                "hours": DecimalQuantityPayload.from_domain(
                    DecimalQuantity.of(str(entry.hours), "HOUR")
                ).model_dump(mode="json"),
            }
            content_hash = canonical_json_sha256(facts)
            latest = outbox.latest_for_aggregate(
                aggregate_type="time_entry", aggregate_id=entry.id
            )
            correction_of_revision: int | None
            if latest is not None:
                prior = ApprovedTimeEntryEventPayload.model_validate(latest.envelope.payload)
                if prior.source_content_hash == content_hash:
                    continue
                revision = latest.envelope.aggregate_version + 1
                correction_of_revision = latest.envelope.aggregate_version
            else:
                revision = 1
                correction_of_revision = None
            payload = ApprovedTimeEntryEventPayload(
                **facts,
                approved_snapshot_id=generate_id(),
                source_revision=revision,
                source_content_hash=content_hash,
                approved_at=approved_at,
                correction_of_revision=correction_of_revision,
            )
            outbox.enqueue(
                IntegrationEventEnvelope(
                    event_id=generate_id(),
                    event_type=APPROVED_TIME_ENTRY_EVENT_TYPE,
                    schema_version=1,
                    tenant_id=context.tenant_id,
                    organization_id=context.organization_id,
                    aggregate_type="time_entry",
                    aggregate_id=entry.id,
                    aggregate_version=revision,
                    occurred_at=approved_at,
                    correlation_id=period.id,
                    payload=payload.model_dump(mode="json"),
                )
            )
            emitted += 1
        return emitted


__all__ = ["ApprovedTimeEventPublisher"]
