from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class StoreroomCreated:
    tenant_id: str
    organization_id: str
    storeroom_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class StoreroomProfileUpdated:
    tenant_id: str
    organization_id: str
    storeroom_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class StoreroomStatusChanged:
    tenant_id: str
    organization_id: str
    storeroom_id: str
    status: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class LocationCreated:
    tenant_id: str
    organization_id: str
    location_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class LocationProfileUpdated:
    tenant_id: str
    organization_id: str
    location_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryReorderPolicyConfigured:
    """One typed event for the single `upsert_reorder_policy` business operation (P25) --
    the caller "saves" the policy for an Item+Storeroom(+Location) scope, and the backend
    decides create vs. update by natural-key lookup; the caller never distinguishes the two,
    so this is not split into Created/Updated. `stock_item_id`/`storeroom_id`/`location_id` are
    the policy's real business identity (`policy_id` alone is an opaque surrogate key)."""

    tenant_id: str
    organization_id: str
    policy_id: str
    stock_item_id: str
    storeroom_id: str
    location_id: str | None
    occurred_at: datetime


__all__ = [
    "StoreroomCreated",
    "StoreroomProfileUpdated",
    "StoreroomStatusChanged",
    "LocationCreated",
    "LocationProfileUpdated",
    "InventoryReorderPolicyConfigured",
]
