from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    BillingExternalEventType,
)
from src.core.platform.contract.port.integration.external_accounting import (
    ExternalAccountingFailureKind,
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


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingPreparationLineRemoved:
    tenant_id: str
    organization_id: str
    project_id: str
    billing_preparation_id: str
    preparation_line_id: str
    source_type: BillableSourceType
    occurred_at: datetime


class BillingPreparationStatusChangeType(str, Enum):
    CANCELLED = "CANCELLED"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELIVERY_PENDING = "DELIVERY_PENDING"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RECONCILED = "RECONCILED"


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingPreparationStatusChanged:
    """Governed local preparation status, including the atomic handoff request.

    Transport and authenticated external outcomes emit their own narrowly scoped
    facts; they do not imply commercial amount or profitability changes.
    """

    tenant_id: str
    organization_id: str
    project_id: str
    billing_preparation_id: str
    change_type: BillingPreparationStatusChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BillingPreparationExternalOutcomeRecorded:
    """Authenticated Accounting business evidence committed with inbox and status.

    Not transport acceptance, invoice issuance or payment. Invalidation is limited
    to Billing/Accounting Status, even when preparation acknowledgement changes.
    """

    tenant_id: str
    organization_id: str
    project_id: str
    billing_preparation_id: str
    external_event_id: str
    event_type: BillingExternalEventType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountingTransportFinalized:
    """Committed transport state only; never commercial profitability authority."""

    tenant_id: str
    organization_id: str
    project_id: str
    handoff_id: str
    result: ExternalAccountingFailureKind | Literal["transport_accepted"]
    occurred_at: datetime


__all__ = [
    "AccountingTransportFinalized",
    "BillingPreparationCreated",
    "BillingPreparationExternalOutcomeRecorded",
    "BillingPreparationLineAdded",
    "BillingPreparationLineRemoved",
    "BillingPreparationStatusChangeType",
    "BillingPreparationStatusChanged",
    "BillingProfileActivated",
    "BillingProfileCreated",
    "BillingScheduleLineAdded",
    "BillingScheduleLineMarkedReady",
]
