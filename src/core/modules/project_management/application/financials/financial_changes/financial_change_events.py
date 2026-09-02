from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class FinancialChangeEventType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    IMPACT_ADDED = "IMPACT_ADDED"
    IMPACT_UPDATED = "IMPACT_UPDATED"
    IMPACT_REMOVED = "IMPACT_REMOVED"
    SUBMITTED = "SUBMITTED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True, kw_only=True)
class FinancialChangeChanged:
    tenant_id: str
    organization_id: str
    project_id: str
    change_id: str
    change_type: FinancialChangeEventType
    occurred_at: datetime
    impact_id: str | None = None
    applied_effects: tuple[str, ...] = ()


__all__ = ["FinancialChangeChanged", "FinancialChangeEventType"]
