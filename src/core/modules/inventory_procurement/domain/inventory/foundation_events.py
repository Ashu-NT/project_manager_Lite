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


__all__ = [
    "StoreroomCreated",
    "StoreroomProfileUpdated",
    "StoreroomStatusChanged",
    "LocationCreated",
    "LocationProfileUpdated",
]
