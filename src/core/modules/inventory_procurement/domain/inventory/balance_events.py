from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class StockOnHandQuantityChanged:
    tenant_id: str
    organization_id: str
    balance_id: str
    stock_item_id: str
    storeroom_id: str
    quantity_delta: float
    resulting_quantity: float
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class StockReservedQuantityChanged:
    tenant_id: str
    organization_id: str
    balance_id: str
    stock_item_id: str
    storeroom_id: str
    quantity_delta: float
    resulting_quantity: float
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class StockOnOrderQuantityChanged:
    tenant_id: str
    organization_id: str
    balance_id: str
    stock_item_id: str
    storeroom_id: str
    quantity_delta: float
    resulting_quantity: float
    occurred_at: datetime


__all__ = [
    "StockOnHandQuantityChanged",
    "StockReservedQuantityChanged",
    "StockOnOrderQuantityChanged",
]
