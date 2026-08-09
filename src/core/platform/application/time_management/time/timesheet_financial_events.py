from __future__ import annotations

from datetime import datetime

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.common.ids import generate_id
from src.core.platform.finance import DecimalQuantity, DecimalQuantityPayload
from src.core.platform.integration import (
    APPROVED_TIME_ENTRY_EVENT_TYPE,
    ApprovedTimeEntryEventPayload,
    IntegrationEventEnvelope,
)
from src.core.platform.integration.canonical_json import canonical_json_sha256


class TimesheetFinancialEventsMixin:
    def _enqueue_approved_time_events(self, *, period, entries: list) -> int:
        outbox = getattr(self, "_approved_time_outbox_service", None)
        if outbox is None:
            return 0
        context = self._tenant_context_service.require_active_scope_ids(
            operation_label="publish approved time"
        )
        approved_at = period.decided_at
        if approved_at is None:
            raise BusinessRuleError(
                "Approved timesheet period is missing its decision timestamp.",
                code="APPROVED_TIME_TIMESTAMP_REQUIRED",
            )
        emitted = 0
        for entry in entries:
            project_id = self._resolve_entry_project_id(entry=entry)
            if not project_id:
                continue
            allocation = self._work_allocation_repo.get(entry.work_allocation_id)
            task_id = getattr(allocation, "task_id", None) if allocation is not None else None
            if entry.organization_id and entry.organization_id != context.organization_id:
                raise BusinessRuleError(
                    "Approved Time entry is outside the active organization.",
                    code="APPROVED_TIME_SCOPE_MISMATCH",
                )
            facts = {
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


__all__ = ["TimesheetFinancialEventsMixin"]
