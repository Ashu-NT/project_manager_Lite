from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.modules.inventory_procurement.domain import (
    PurchaseRequisition,
    PurchaseRequisitionLine,
    StockReservation,
    StockTransaction,
)


class MaintenanceMaterialAvailabilityStatus(str, Enum):
    AVAILABLE_FROM_STOCK = "AVAILABLE_FROM_STOCK"
    PARTIALLY_AVAILABLE_FROM_STOCK = "PARTIALLY_AVAILABLE_FROM_STOCK"
    UNAVAILABLE_FROM_STOCK = "UNAVAILABLE_FROM_STOCK"
    DIRECT_PROCUREMENT_ONLY = "DIRECT_PROCUREMENT_ONLY"
    NOT_MAINTENANCE_ENABLED = "NOT_MAINTENANCE_ENABLED"


@dataclass(frozen=True)
class MaintenanceMaterialAvailability:
    source_reference_type: str
    source_reference_id: str
    stock_item_id: str
    storeroom_id: str
    requested_qty: float
    requested_uom: str
    requested_stock_qty: float
    on_hand_stock_qty: float
    reserved_stock_qty: float
    available_stock_qty: float
    on_order_stock_qty: float
    missing_stock_qty: float
    status: MaintenanceMaterialAvailabilityStatus
    can_reserve: bool
    can_issue_from_stock: bool
    can_direct_procure: bool


@dataclass(frozen=True)
class MaintenanceMaterialProcurementEscalation:
    source_reference_type: str
    source_reference_id: str
    availability: MaintenanceMaterialAvailability
    requisition: PurchaseRequisition
    requisition_line: PurchaseRequisitionLine
    auto_submitted: bool


@dataclass(frozen=True)
class MaintenanceMaterialExecutionResult:
    source_reference_type: str
    source_reference_id: str
    availability: MaintenanceMaterialAvailability
    reservation: StockReservation | None = None
    transaction: StockTransaction | None = None


__all__ = [
    "MaintenanceMaterialAvailability",
    "MaintenanceMaterialAvailabilityStatus",
    "MaintenanceMaterialExecutionResult",
    "MaintenanceMaterialProcurementEscalation",
]
