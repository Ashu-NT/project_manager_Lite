from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryReservationCreated:
    tenant_id: str
    organization_id: str
    reservation_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryReservationConsumptionAdvanced:
    tenant_id: str
    organization_id: str
    reservation_id: str
    resulting_status: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryReservationReleased:
    tenant_id: str
    organization_id: str
    reservation_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryReservationCancelled:
    tenant_id: str
    organization_id: str
    reservation_id: str
    occurred_at: datetime


__all__ = [
    "InventoryReservationCreated",
    "InventoryReservationConsumptionAdvanced",
    "InventoryReservationReleased",
    "InventoryReservationCancelled",
]
