from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    BillingExternalEventType,
)

# ---------------------------------------------------------------------------
# Billing Profile family (ProjectBillingProfile / ProjectBillingScheduleLine)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingProfileCreated:
    tenant_id: str
    organization_id: str
    project_id: str
    billing_profile_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingProfileActivated:
    """The only currently-reachable Profile status transition -- `place_on_hold`/`close` exist as
    domain methods but have no service-layer command, so ON_HOLD/CLOSED are unreachable and no
    event vocabulary is invented for them. A single specific fact (rather than a `change_type`
    enum with one member) mirrors this being genuinely the only reachable transition today."""

    tenant_id: str
    organization_id: str
    project_id: str
    billing_profile_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingScheduleLineAdded:
    tenant_id: str
    organization_id: str
    project_id: str
    billing_profile_id: str
    schedule_line_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingScheduleLineMarkedReady:
    """The only currently-reachable schedule-line status transition -- `mark_billed`/`cancel`
    exist as domain methods but have no service-layer command."""

    tenant_id: str
    organization_id: str
    project_id: str
    billing_profile_id: str
    schedule_line_id: str
    occurred_at: datetime


# ---------------------------------------------------------------------------
# Billing Preparation family (ProjectBillingPreparation / *Line / *SourceLock / *ExternalEvent)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingPreparationCreated:
    tenant_id: str
    organization_id: str
    project_id: str
    billing_preparation_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingPreparationLineAdded:
    """`add_fixed_price_source`/`add_approved_time_source`/`add_cost_plus_source` are the same
    kind of fact (a preparation line was added and its source reserved), differentiated by
    `source_type` -- the reused domain `BillableSourceType` enum, not a duplicate. The
    `ProjectBillingSourceLock` row created alongside the line is infrastructure (prevents the same
    source being billed twice), not an independent business fact -- no separate lock event."""

    tenant_id: str
    organization_id: str
    project_id: str
    billing_preparation_id: str
    preparation_line_id: str
    source_type: BillableSourceType
    occurred_at: datetime


class BillingPreparationStatusChangeType(str, Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELIVERY_PENDING = "DELIVERY_PENDING"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RECONCILED = "RECONCILED"


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingPreparationStatusChanged:
    """`submit`/`approve`/`reject`/`request_delivery` and the status-transitioning branches of
    `record_external_outcome` are all the same kind of fact (the preparation's status field
    changed), differentiated by `change_type` -- mirroring Budget's/Cost Entry's own
    status-transition shape. `request_delivery` produces no separate durable fact beyond this
    status change: it returns an in-memory delivery payload to its caller but persists nothing
    else (no outbox row, no allocated external identifier) -- confirmed by direct source reading,
    not assumed; a `BillingPreparationDeliveryRequested` fact was considered and found
    unnecessary. `record_external_outcome(DELIVERY_ACCEPTED)` transitions status twice in one call
    (`mark_delivered` then `acknowledge`, both persisted) -- both are recorded as two separate
    facts, one per actual status transition, mirroring Budget's approve/supersede precedent.
    `CANCELLED` has no service-layer command and is not represented."""

    tenant_id: str
    organization_id: str
    project_id: str
    billing_preparation_id: str
    change_type: BillingPreparationStatusChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingPreparationExternalOutcomeRecorded:
    """`record_external_outcome` -- the external accounting system's business response (delivery
    acceptance/rejection, status update, reconciliation), not merely the `ProjectBillingExternalEvent`
    ORM row's existence. Coexists with `BillingPreparationStatusChanged` when the outcome also
    transitions status (both are genuine, separately meaningful persisted facts)."""

    tenant_id: str
    organization_id: str
    project_id: str
    billing_preparation_id: str
    external_event_id: str
    event_type: BillingExternalEventType
    occurred_at: datetime


__all__ = [
    "BillingProfileCreated",
    "BillingProfileActivated",
    "BillingScheduleLineAdded",
    "BillingScheduleLineMarkedReady",
    "BillingPreparationCreated",
    "BillingPreparationLineAdded",
    "BillingPreparationStatusChangeType",
    "BillingPreparationStatusChanged",
    "BillingPreparationExternalOutcomeRecorded",
]
