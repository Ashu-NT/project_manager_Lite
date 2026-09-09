from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.core.modules.project_management.domain.risk.register import RegisterEntryType


class RegisterEntryChangeType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisterEntryChanged:
    """`create_entry`/`update_entry`/`delete_entry` are all the same kind of fact (a
    `RegisterEntry` changed), differentiated by `change_type` -- mirrors `BudgetStatusChanged`'s
    shared-family precedent. `RegisterEntry` is one cohesive aggregate with a RISK|ISSUE|CHANGE
    discriminator field, not three separate aggregates, so this is one event class, not three."""

    tenant_id: str
    organization_id: str
    project_id: str
    register_entry_id: str
    entry_type: RegisterEntryType
    change_type: RegisterEntryChangeType
    occurred_at: datetime


__all__ = ["RegisterEntryChangeType", "RegisterEntryChanged"]
