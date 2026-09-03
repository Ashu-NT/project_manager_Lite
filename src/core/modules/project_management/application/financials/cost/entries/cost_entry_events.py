from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CostEntryRecorded:

    tenant_id: str
    organization_id: str
    project_id: str
    cost_entry_id: str
    status: ProjectCostEntryStatus
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CostEntryUpdated:
    """A draft entry's content was edited (`update_draft`) -- genuine mutable-CRUD, not a
    lifecycle-status transition."""

    tenant_id: str
    organization_id: str
    project_id: str
    cost_entry_id: str
    occurred_at: datetime


class CostEntryStatusChangeType(str, Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    POSTED = "POSTED"


@dataclass(frozen=True, slots=True, kw_only=True)
class CostEntryStatusChanged:
    """A workflow decision advanced (or returned) the entry's lifecycle stage -- `submit`,
    `approve`, `reject`, `post` are all the same kind of fact (the entry's status field changed),
    differentiated by `change_type`, not by four near-identical classes. `REJECTED` corresponds
    to the domain's own `reject()`, which returns the entry to DRAFT status with rejection
    metadata -- `change_type` disambiguates that from a fresh DRAFT creation, which
    `entry.status` alone cannot."""

    tenant_id: str
    organization_id: str
    project_id: str
    cost_entry_id: str
    change_type: CostEntryStatusChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CostEntryReversed:
    """A posted entry was reversed and a new, immutable reversal entry was recorded -- a genuine
    financial-correction fact, produced by the manual `reverse` command and by the
    correction-of-a-prior-revision branch inside `apply_approved_time_source`. `cost_entry_id` is
    the new reversal entry's id; `reverses_entry_id` is the original entry it corrects."""

    tenant_id: str
    organization_id: str
    project_id: str
    cost_entry_id: str
    reverses_entry_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CostEntryRemoved:
    """A draft entry was deleted (`delete_draft`)."""

    tenant_id: str
    organization_id: str
    project_id: str
    cost_entry_id: str
    occurred_at: datetime


__all__ = [
    "CostEntryRecorded",
    "CostEntryUpdated",
    "CostEntryStatusChangeType",
    "CostEntryStatusChanged",
    "CostEntryReversed",
    "CostEntryRemoved",
]
