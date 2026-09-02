from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderCreated:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderLineAdded:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    purchase_order_line_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderProfileUpdated:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderSubmitted:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    approval_request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderApproved:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    approval_request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderRejected:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    approval_request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderCancelled:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderSent:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderClosed:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryPurchaseOrderReceivingAdvanced:
    tenant_id: str
    organization_id: str
    purchase_order_id: str
    resulting_status: str
    occurred_at: datetime


__all__ = [
    "InventoryPurchaseOrderCreated",
    "InventoryPurchaseOrderLineAdded",
    "InventoryPurchaseOrderProfileUpdated",
    "InventoryPurchaseOrderSubmitted",
    "InventoryPurchaseOrderApproved",
    "InventoryPurchaseOrderRejected",
    "InventoryPurchaseOrderCancelled",
    "InventoryPurchaseOrderSent",
    "InventoryPurchaseOrderClosed",
    "InventoryPurchaseOrderReceivingAdvanced",
]
