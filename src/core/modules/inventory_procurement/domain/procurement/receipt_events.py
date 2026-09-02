from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryReceiptPosted:
    tenant_id: str
    organization_id: str
    receipt_id: str
    purchase_order_id: str
    occurred_at: datetime


__all__ = [
    "InventoryReceiptPosted",
]
