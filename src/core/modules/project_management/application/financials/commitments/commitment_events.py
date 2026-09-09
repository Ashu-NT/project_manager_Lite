from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class CommitmentLineChangeType(str, Enum):
    CREATED = "CREATED"
    REVISED = "REVISED"


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitmentLineChanged:

    tenant_id: str
    organization_id: str
    project_id: str
    commitment_line_id: str
    change_type: CommitmentLineChangeType
    occurred_at: datetime


class CommitmentMatchChangeType(str, Enum):
    MATCHED = "MATCHED"
    REVERSED = "REVERSED"


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitmentMatchChanged:
    """A canonical DomainEvent -- recorded via `uow.record_event(...)` (direct/UI callers) or
    returned for explicit publication (Procurement-inbox callers). A replayed match (the same
    idempotency key seen again) is a true no-op and never reaches this event."""

    tenant_id: str
    organization_id: str
    project_id: str
    commitment_line_id: str
    match_id: str
    change_type: CommitmentMatchChangeType
    occurred_at: datetime


__all__ = [
    "CommitmentLineChangeType",
    "CommitmentLineChanged",
    "CommitmentMatchChangeType",
    "CommitmentMatchChanged",
]
