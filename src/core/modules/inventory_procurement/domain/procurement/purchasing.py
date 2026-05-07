from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from src.core.platform.common.ids import generate_id


class PurchaseRequisitionStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIALLY_SOURCED = "PARTIALLY_SOURCED"
    FULLY_SOURCED = "FULLY_SOURCED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class PurchaseRequisitionLineStatus(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    PARTIALLY_SOURCED = "PARTIALLY_SOURCED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FULLY_SOURCED = "FULLY_SOURCED"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENT = "SENT"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PurchaseOrderLineStatus(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    CANCELLED = "CANCELLED"


class ReceiptStatus(str, Enum):
    POSTED = "POSTED"


@dataclass
class PurchaseRequisition:
    id: str
    organization_id: str
    requisition_number: str
    requesting_site_id: str
    requesting_storeroom_id: str
    requester_user_id: str | None = None
    requester_username: str = ""
    status: PurchaseRequisitionStatus = PurchaseRequisitionStatus.DRAFT
    purpose: str = ""
    needed_by_date: date | None = None
    priority: str = ""
    approval_request_id: str | None = None
    source_reference_type: str = ""
    source_reference_id: str = ""
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        requisition_number: str,
        requesting_site_id: str,
        requesting_storeroom_id: str,
        requester_user_id: str | None = None,
        requester_username: str = "",
        status: PurchaseRequisitionStatus = PurchaseRequisitionStatus.DRAFT,
        purpose: str = "",
        needed_by_date: date | None = None,
        priority: str = "",
        approval_request_id: str | None = None,
        source_reference_type: str = "",
        source_reference_id: str = "",
        submitted_at: datetime | None = None,
        approved_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        notes: str = "",
    ) -> "PurchaseRequisition":
        now = datetime.now(timezone.utc)
        return PurchaseRequisition(
            id=generate_id(),
            organization_id=organization_id,
            requisition_number=requisition_number,
            requesting_site_id=requesting_site_id,
            requesting_storeroom_id=requesting_storeroom_id,
            requester_user_id=requester_user_id,
            requester_username=requester_username,
            status=status,
            purpose=purpose,
            needed_by_date=needed_by_date,
            priority=priority,
            approval_request_id=approval_request_id,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            submitted_at=submitted_at,
            approved_at=approved_at,
            cancelled_at=cancelled_at,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class PurchaseRequisitionLine:
    id: str
    purchase_requisition_id: str
    line_number: int
    stock_item_id: str
    description: str = ""
    quantity_requested: float = 0.0
    uom: str = ""
    needed_by_date: date | None = None
    estimated_unit_cost: float = 0.0
    quantity_sourced: float = 0.0
    suggested_supplier_party_id: str | None = None
    status: PurchaseRequisitionLineStatus = PurchaseRequisitionLineStatus.DRAFT
    notes: str = ""

    @staticmethod
    def create(
        *,
        purchase_requisition_id: str,
        line_number: int,
        stock_item_id: str,
        description: str = "",
        quantity_requested: float,
        uom: str,
        needed_by_date: date | None = None,
        estimated_unit_cost: float = 0.0,
        quantity_sourced: float = 0.0,
        suggested_supplier_party_id: str | None = None,
        status: PurchaseRequisitionLineStatus = PurchaseRequisitionLineStatus.DRAFT,
        notes: str = "",
    ) -> "PurchaseRequisitionLine":
        return PurchaseRequisitionLine(
            id=generate_id(),
            purchase_requisition_id=purchase_requisition_id,
            line_number=line_number,
            stock_item_id=stock_item_id,
            description=description,
            quantity_requested=quantity_requested,
            uom=uom,
            needed_by_date=needed_by_date,
            estimated_unit_cost=estimated_unit_cost,
            quantity_sourced=quantity_sourced,
            suggested_supplier_party_id=suggested_supplier_party_id,
            status=status,
            notes=notes,
        )


@dataclass
class PurchaseOrder:
    id: str
    organization_id: str
    po_number: str
    site_id: str
    supplier_party_id: str
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    order_date: date | None = None
    expected_delivery_date: date | None = None
    currency_code: str = ""
    approval_request_id: str | None = None
    source_requisition_id: str | None = None
    supplier_reference: str = ""
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    closed_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        po_number: str,
        site_id: str,
        supplier_party_id: str,
        status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT,
        order_date: date | None = None,
        expected_delivery_date: date | None = None,
        currency_code: str = "",
        approval_request_id: str | None = None,
        source_requisition_id: str | None = None,
        supplier_reference: str = "",
        submitted_at: datetime | None = None,
        approved_at: datetime | None = None,
        sent_at: datetime | None = None,
        closed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        notes: str = "",
    ) -> "PurchaseOrder":
        now = datetime.now(timezone.utc)
        return PurchaseOrder(
            id=generate_id(),
            organization_id=organization_id,
            po_number=po_number,
            site_id=site_id,
            supplier_party_id=supplier_party_id,
            status=status,
            order_date=order_date,
            expected_delivery_date=expected_delivery_date,
            currency_code=currency_code,
            approval_request_id=approval_request_id,
            source_requisition_id=source_requisition_id,
            supplier_reference=supplier_reference,
            submitted_at=submitted_at,
            approved_at=approved_at,
            sent_at=sent_at,
            closed_at=closed_at,
            cancelled_at=cancelled_at,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class PurchaseOrderLine:
    id: str
    purchase_order_id: str
    line_number: int
    stock_item_id: str
    destination_storeroom_id: str
    description: str = ""
    quantity_ordered: float = 0.0
    quantity_received: float = 0.0
    quantity_rejected: float = 0.0
    uom: str = ""
    unit_price: float = 0.0
    expected_delivery_date: date | None = None
    source_requisition_line_id: str | None = None
    status: PurchaseOrderLineStatus = PurchaseOrderLineStatus.DRAFT
    notes: str = ""

    @staticmethod
    def create(
        *,
        purchase_order_id: str,
        line_number: int,
        stock_item_id: str,
        destination_storeroom_id: str,
        quantity_ordered: float,
        uom: str,
        description: str = "",
        quantity_received: float = 0.0,
        quantity_rejected: float = 0.0,
        unit_price: float = 0.0,
        expected_delivery_date: date | None = None,
        source_requisition_line_id: str | None = None,
        status: PurchaseOrderLineStatus = PurchaseOrderLineStatus.DRAFT,
        notes: str = "",
    ) -> "PurchaseOrderLine":
        return PurchaseOrderLine(
            id=generate_id(),
            purchase_order_id=purchase_order_id,
            line_number=line_number,
            stock_item_id=stock_item_id,
            destination_storeroom_id=destination_storeroom_id,
            description=description,
            quantity_ordered=quantity_ordered,
            quantity_received=quantity_received,
            quantity_rejected=quantity_rejected,
            uom=uom,
            unit_price=unit_price,
            expected_delivery_date=expected_delivery_date,
            source_requisition_line_id=source_requisition_line_id,
            status=status,
            notes=notes,
        )


@dataclass
class ReceiptHeader:
    id: str
    organization_id: str
    receipt_number: str
    purchase_order_id: str
    received_site_id: str
    supplier_party_id: str
    status: ReceiptStatus = ReceiptStatus.POSTED
    receipt_date: datetime | None = None
    supplier_delivery_reference: str = ""
    received_by_user_id: str | None = None
    received_by_username: str = ""
    notes: str = ""
    created_at: datetime | None = None

    @staticmethod
    def create(
        *,
        organization_id: str,
        receipt_number: str,
        purchase_order_id: str,
        received_site_id: str,
        supplier_party_id: str,
        status: ReceiptStatus = ReceiptStatus.POSTED,
        receipt_date: datetime | None = None,
        supplier_delivery_reference: str = "",
        received_by_user_id: str | None = None,
        received_by_username: str = "",
        notes: str = "",
    ) -> "ReceiptHeader":
        now = datetime.now(timezone.utc)
        effective_receipt_date = receipt_date or now
        return ReceiptHeader(
            id=generate_id(),
            organization_id=organization_id,
            receipt_number=receipt_number,
            purchase_order_id=purchase_order_id,
            received_site_id=received_site_id,
            supplier_party_id=supplier_party_id,
            status=status,
            receipt_date=effective_receipt_date,
            supplier_delivery_reference=supplier_delivery_reference,
            received_by_user_id=received_by_user_id,
            received_by_username=received_by_username,
            notes=notes,
            created_at=now,
        )


@dataclass
class ReceiptLine:
    id: str
    receipt_header_id: str
    purchase_order_line_id: str
    line_number: int
    stock_item_id: str
    storeroom_id: str
    quantity_accepted: float = 0.0
    quantity_rejected: float = 0.0
    uom: str = ""
    unit_cost: float = 0.0
    lot_number: str = ""
    serial_number: str = ""
    expiry_date: date | None = None
    notes: str = ""

    @staticmethod
    def create(
        *,
        receipt_header_id: str,
        purchase_order_line_id: str,
        line_number: int,
        stock_item_id: str,
        storeroom_id: str,
        quantity_accepted: float,
        quantity_rejected: float = 0.0,
        uom: str,
        unit_cost: float = 0.0,
        lot_number: str = "",
        serial_number: str = "",
        expiry_date: date | None = None,
        notes: str = "",
    ) -> "ReceiptLine":
        return ReceiptLine(
            id=generate_id(),
            receipt_header_id=receipt_header_id,
            purchase_order_line_id=purchase_order_line_id,
            line_number=line_number,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            quantity_accepted=quantity_accepted,
            quantity_rejected=quantity_rejected,
            uom=uom,
            unit_cost=unit_cost,
            lot_number=lot_number,
            serial_number=serial_number,
            expiry_date=expiry_date,
            notes=notes,
        )


__all__ = [
    "PurchaseOrder",
    "PurchaseOrderLine",
    "PurchaseOrderLineStatus",
    "PurchaseOrderStatus",
    "PurchaseRequisition",
    "PurchaseRequisitionLine",
    "PurchaseRequisitionLineStatus",
    "PurchaseRequisitionStatus",
    "ReceiptHeader",
    "ReceiptLine",
    "ReceiptStatus",
]
