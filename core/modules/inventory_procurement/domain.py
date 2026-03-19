from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from core.modules.project_management.domain.identifiers import generate_id


class StockTransactionType(str, Enum):
    OPENING_BALANCE = "OPENING_BALANCE"
    ADJUSTMENT_INCREASE = "ADJUSTMENT_INCREASE"
    ADJUSTMENT_DECREASE = "ADJUSTMENT_DECREASE"
    ISSUE = "ISSUE"
    RETURN = "RETURN"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    RESERVATION_HOLD = "RESERVATION_HOLD"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"


class StockReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PARTIALLY_ISSUED = "PARTIALLY_ISSUED"
    FULLY_ISSUED = "FULLY_ISSUED"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"


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
class StockItem:
    id: str
    organization_id: str
    item_code: str
    name: str
    description: str = ""
    item_type: str = ""
    status: str = "DRAFT"
    stock_uom: str = ""
    order_uom: str = ""
    issue_uom: str = ""
    category_code: str = ""
    commodity_code: str = ""
    is_stocked: bool = True
    is_purchase_allowed: bool = True
    is_active: bool = False
    default_reorder_policy: str = ""
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    lead_time_days: int | None = None
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    shelf_life_days: int | None = None
    preferred_party_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        item_code: str,
        name: str,
        description: str = "",
        item_type: str = "",
        status: str = "DRAFT",
        stock_uom: str,
        order_uom: str = "",
        issue_uom: str = "",
        category_code: str = "",
        commodity_code: str = "",
        is_stocked: bool = True,
        is_purchase_allowed: bool = True,
        is_active: bool = False,
        default_reorder_policy: str = "",
        min_qty: float = 0.0,
        max_qty: float = 0.0,
        reorder_point: float = 0.0,
        reorder_qty: float = 0.0,
        lead_time_days: int | None = None,
        is_lot_tracked: bool = False,
        is_serial_tracked: bool = False,
        shelf_life_days: int | None = None,
        preferred_party_id: str | None = None,
        notes: str = "",
    ) -> "StockItem":
        now = datetime.now(timezone.utc)
        return StockItem(
            id=generate_id(),
            organization_id=organization_id,
            item_code=item_code,
            name=name,
            description=description,
            item_type=item_type,
            status=status,
            stock_uom=stock_uom,
            order_uom=order_uom,
            issue_uom=issue_uom,
            category_code=category_code,
            commodity_code=commodity_code,
            is_stocked=is_stocked,
            is_purchase_allowed=is_purchase_allowed,
            is_active=is_active,
            default_reorder_policy=default_reorder_policy,
            min_qty=min_qty,
            max_qty=max_qty,
            reorder_point=reorder_point,
            reorder_qty=reorder_qty,
            lead_time_days=lead_time_days,
            is_lot_tracked=is_lot_tracked,
            is_serial_tracked=is_serial_tracked,
            shelf_life_days=shelf_life_days,
            preferred_party_id=preferred_party_id,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


@dataclass
class Storeroom:
    id: str
    organization_id: str
    storeroom_code: str
    name: str
    description: str = ""
    site_id: str = ""
    status: str = "DRAFT"
    storeroom_type: str = ""
    is_active: bool = False
    is_internal_supplier: bool = False
    allows_issue: bool = True
    allows_transfer: bool = True
    allows_receiving: bool = True
    default_currency_code: str = ""
    manager_party_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        storeroom_code: str,
        name: str,
        site_id: str,
        description: str = "",
        status: str = "DRAFT",
        storeroom_type: str = "",
        is_active: bool = False,
        is_internal_supplier: bool = False,
        allows_issue: bool = True,
        allows_transfer: bool = True,
        allows_receiving: bool = True,
        default_currency_code: str = "",
        manager_party_id: str | None = None,
        notes: str = "",
    ) -> "Storeroom":
        now = datetime.now(timezone.utc)
        return Storeroom(
            id=generate_id(),
            organization_id=organization_id,
            storeroom_code=storeroom_code,
            name=name,
            description=description,
            site_id=site_id,
            status=status,
            storeroom_type=storeroom_type,
            is_active=is_active,
            is_internal_supplier=is_internal_supplier,
            allows_issue=allows_issue,
            allows_transfer=allows_transfer,
            allows_receiving=allows_receiving,
            default_currency_code=default_currency_code,
            manager_party_id=manager_party_id,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


@dataclass
class StockBalance:
    id: str
    organization_id: str
    stock_item_id: str
    storeroom_id: str
    uom: str
    on_hand_qty: float = 0.0
    reserved_qty: float = 0.0
    available_qty: float = 0.0
    on_order_qty: float = 0.0
    committed_qty: float = 0.0
    average_cost: float = 0.0
    last_receipt_at: datetime | None = None
    last_issue_at: datetime | None = None
    reorder_required: bool = False
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        stock_item_id: str,
        storeroom_id: str,
        uom: str,
    ) -> "StockBalance":
        now = datetime.now(timezone.utc)
        return StockBalance(
            id=generate_id(),
            organization_id=organization_id,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            uom=uom,
            updated_at=now,
            version=1,
        )


@dataclass
class StockTransaction:
    id: str
    organization_id: str
    transaction_number: str
    stock_item_id: str
    storeroom_id: str
    transaction_type: StockTransactionType
    quantity: float
    uom: str
    unit_cost: float = 0.0
    transaction_at: datetime | None = None
    reference_type: str = ""
    reference_id: str = ""
    performed_by_user_id: str | None = None
    performed_by_username: str = ""
    resulting_on_hand_qty: float = 0.0
    resulting_available_qty: float = 0.0
    notes: str = ""

    @staticmethod
    def create(
        *,
        organization_id: str,
        transaction_number: str,
        stock_item_id: str,
        storeroom_id: str,
        transaction_type: StockTransactionType,
        quantity: float,
        uom: str,
        unit_cost: float = 0.0,
        transaction_at: datetime | None = None,
        reference_type: str = "",
        reference_id: str = "",
        performed_by_user_id: str | None = None,
        performed_by_username: str = "",
        resulting_on_hand_qty: float = 0.0,
        resulting_available_qty: float = 0.0,
        notes: str = "",
    ) -> "StockTransaction":
        return StockTransaction(
            id=generate_id(),
            organization_id=organization_id,
            transaction_number=transaction_number,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            transaction_type=transaction_type,
            quantity=quantity,
            uom=uom,
            unit_cost=unit_cost,
            transaction_at=transaction_at or datetime.now(timezone.utc),
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by_user_id=performed_by_user_id,
            performed_by_username=performed_by_username,
            resulting_on_hand_qty=resulting_on_hand_qty,
            resulting_available_qty=resulting_available_qty,
            notes=notes,
        )


@dataclass
class StockReservation:
    id: str
    organization_id: str
    reservation_number: str
    stock_item_id: str
    storeroom_id: str
    reserved_qty: float
    issued_qty: float = 0.0
    remaining_qty: float = 0.0
    uom: str = ""
    status: StockReservationStatus = StockReservationStatus.ACTIVE
    need_by_date: date | None = None
    source_reference_type: str = ""
    source_reference_id: str = ""
    requested_by_user_id: str | None = None
    requested_by_username: str = ""
    created_at: datetime | None = None
    released_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        reservation_number: str,
        stock_item_id: str,
        storeroom_id: str,
        reserved_qty: float,
        uom: str,
        issued_qty: float = 0.0,
        remaining_qty: float | None = None,
        status: StockReservationStatus = StockReservationStatus.ACTIVE,
        need_by_date: date | None = None,
        source_reference_type: str = "",
        source_reference_id: str = "",
        requested_by_user_id: str | None = None,
        requested_by_username: str = "",
        released_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        notes: str = "",
    ) -> "StockReservation":
        now = datetime.now(timezone.utc)
        effective_remaining = (
            float(remaining_qty)
            if remaining_qty is not None
            else max(0.0, float(reserved_qty or 0.0) - float(issued_qty or 0.0))
        )
        return StockReservation(
            id=generate_id(),
            organization_id=organization_id,
            reservation_number=reservation_number,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            reserved_qty=reserved_qty,
            issued_qty=issued_qty,
            remaining_qty=effective_remaining,
            uom=uom,
            status=status,
            need_by_date=need_by_date,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            requested_by_user_id=requested_by_user_id,
            requested_by_username=requested_by_username,
            created_at=now,
            released_at=released_at,
            cancelled_at=cancelled_at,
            notes=notes,
            version=1,
        )


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
            notes=notes,
        )


__all__ = [
    "StockBalance",
    "StockItem",
    "PurchaseRequisition",
    "PurchaseRequisitionLine",
    "PurchaseRequisitionLineStatus",
    "PurchaseRequisitionStatus",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "PurchaseOrderLineStatus",
    "PurchaseOrderStatus",
    "ReceiptHeader",
    "ReceiptLine",
    "ReceiptStatus",
    "StockReservation",
    "StockReservationStatus",
    "StockTransaction",
    "StockTransactionType",
    "Storeroom",
]
