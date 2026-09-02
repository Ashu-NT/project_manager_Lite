from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryItemCreated:
    tenant_id: str
    organization_id: str
    item_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryItemProfileUpdated:
    tenant_id: str
    organization_id: str
    item_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryItemStatusChanged:
    tenant_id: str
    organization_id: str
    item_id: str
    status: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryItemCategoryCreated:
    tenant_id: str
    organization_id: str
    category_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryItemCategoryProfileUpdated:
    tenant_id: str
    organization_id: str
    category_id: str
    occurred_at: datetime


__all__ = [
    "InventoryItemCreated",
    "InventoryItemProfileUpdated",
    "InventoryItemStatusChanged",
    "InventoryItemCategoryCreated",
    "InventoryItemCategoryProfileUpdated",
]
