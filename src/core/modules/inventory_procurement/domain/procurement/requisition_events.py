from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryRequisitionCreated:
    tenant_id: str
    organization_id: str
    requisition_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryRequisitionLineAdded:
    tenant_id: str
    organization_id: str
    requisition_id: str
    requisition_line_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryRequisitionProfileUpdated:
    tenant_id: str
    organization_id: str
    requisition_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryRequisitionSubmitted:
    tenant_id: str
    organization_id: str
    requisition_id: str
    approval_request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryRequisitionApproved:
    tenant_id: str
    organization_id: str
    requisition_id: str
    approval_request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryRequisitionRejected:
    tenant_id: str
    organization_id: str
    requisition_id: str
    approval_request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryRequisitionCancelled:
    tenant_id: str
    organization_id: str
    requisition_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryRequisitionSourcingAdvanced:
    tenant_id: str
    organization_id: str
    requisition_id: str
    purchase_order_id: str
    resulting_status: str
    occurred_at: datetime


__all__ = [
    "InventoryRequisitionCreated",
    "InventoryRequisitionLineAdded",
    "InventoryRequisitionProfileUpdated",
    "InventoryRequisitionSubmitted",
    "InventoryRequisitionApproved",
    "InventoryRequisitionRejected",
    "InventoryRequisitionCancelled",
    "InventoryRequisitionSourcingAdvanced",
]
