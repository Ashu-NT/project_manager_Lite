from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryCycleCountScheduled:
    tenant_id: str
    organization_id: str
    cycle_count_id: str
    storeroom_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryCycleCountCompleted:
    tenant_id: str
    organization_id: str
    cycle_count_id: str
    storeroom_id: str
    variance_qty: float
    occurred_at: datetime


__all__ = [
    "InventoryCycleCountScheduled",
    "InventoryCycleCountCompleted",
]
