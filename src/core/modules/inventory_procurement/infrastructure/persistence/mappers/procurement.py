from __future__ import annotations

from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
    ReceiptHeader,
    ReceiptLine,
    ReceiptStatus,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.procurement import (
    PurchaseOrderLineORM,
    PurchaseOrderORM,
    PurchaseRequisitionLineORM,
    PurchaseRequisitionORM,
    ReceiptHeaderORM,
    ReceiptLineORM,
)


def purchase_requisition_to_orm(requisition: PurchaseRequisition) -> PurchaseRequisitionORM:
    return PurchaseRequisitionORM(
        id=requisition.id,
        organization_id=requisition.organization_id,
        requisition_number=requisition.requisition_number,
        requesting_site_id=requisition.requesting_site_id,
        requesting_storeroom_id=requisition.requesting_storeroom_id,
        requester_user_id=requisition.requester_user_id,
        requester_username=requisition.requester_username or None,
        status=requisition.status,
        purpose=requisition.purpose or None,
        needed_by_date=requisition.needed_by_date,
        priority=requisition.priority or None,
        approval_request_id=requisition.approval_request_id,
        source_reference_type=requisition.source_reference_type or None,
        source_reference_id=requisition.source_reference_id or None,
        submitted_at=requisition.submitted_at,
        approved_at=requisition.approved_at,
        cancelled_at=requisition.cancelled_at,
        notes=requisition.notes or None,
        created_at=requisition.created_at,
        updated_at=requisition.updated_at,
        version=getattr(requisition, "version", 1),
    )


def purchase_requisition_from_orm(obj: PurchaseRequisitionORM) -> PurchaseRequisition:
    return PurchaseRequisition(
        id=obj.id,
        organization_id=obj.organization_id,
        requisition_number=obj.requisition_number,
        requesting_site_id=obj.requesting_site_id,
        requesting_storeroom_id=obj.requesting_storeroom_id,
        requester_user_id=obj.requester_user_id,
        requester_username=obj.requester_username or "",
        status=PurchaseRequisitionStatus(obj.status),
        purpose=obj.purpose or "",
        needed_by_date=obj.needed_by_date,
        priority=obj.priority or "",
        approval_request_id=obj.approval_request_id,
        source_reference_type=obj.source_reference_type or "",
        source_reference_id=obj.source_reference_id or "",
        submitted_at=obj.submitted_at,
        approved_at=obj.approved_at,
        cancelled_at=obj.cancelled_at,
        notes=obj.notes or "",
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
    )


def purchase_requisition_line_to_orm(line: PurchaseRequisitionLine) -> PurchaseRequisitionLineORM:
    return PurchaseRequisitionLineORM(
        id=line.id,
        purchase_requisition_id=line.purchase_requisition_id,
        line_number=line.line_number,
        stock_item_id=line.stock_item_id,
        description=line.description or None,
        quantity_requested=line.quantity_requested,
        uom=line.uom,
        needed_by_date=line.needed_by_date,
        estimated_unit_cost=line.estimated_unit_cost,
        quantity_sourced=line.quantity_sourced,
        suggested_supplier_party_id=line.suggested_supplier_party_id,
        status=line.status,
        notes=line.notes or None,
    )


def purchase_requisition_line_from_orm(obj: PurchaseRequisitionLineORM) -> PurchaseRequisitionLine:
    return PurchaseRequisitionLine(
        id=obj.id,
        purchase_requisition_id=obj.purchase_requisition_id,
        line_number=obj.line_number,
        stock_item_id=obj.stock_item_id,
        description=obj.description or "",
        quantity_requested=float(obj.quantity_requested or 0.0),
        uom=obj.uom,
        needed_by_date=obj.needed_by_date,
        estimated_unit_cost=float(obj.estimated_unit_cost or 0.0),
        quantity_sourced=float(obj.quantity_sourced or 0.0),
        suggested_supplier_party_id=obj.suggested_supplier_party_id,
        status=PurchaseRequisitionLineStatus(obj.status),
        notes=obj.notes or "",
    )


def purchase_order_to_orm(purchase_order: PurchaseOrder) -> PurchaseOrderORM:
    return PurchaseOrderORM(
        id=purchase_order.id,
        organization_id=purchase_order.organization_id,
        po_number=purchase_order.po_number,
        site_id=purchase_order.site_id,
        supplier_party_id=purchase_order.supplier_party_id,
        status=purchase_order.status,
        order_date=purchase_order.order_date,
        expected_delivery_date=purchase_order.expected_delivery_date,
        currency_code=purchase_order.currency_code or None,
        approval_request_id=purchase_order.approval_request_id,
        source_requisition_id=purchase_order.source_requisition_id,
        supplier_reference=purchase_order.supplier_reference or None,
        submitted_at=purchase_order.submitted_at,
        approved_at=purchase_order.approved_at,
        sent_at=purchase_order.sent_at,
        closed_at=purchase_order.closed_at,
        cancelled_at=purchase_order.cancelled_at,
        notes=purchase_order.notes or None,
        created_at=purchase_order.created_at,
        updated_at=purchase_order.updated_at,
        version=getattr(purchase_order, "version", 1),
    )


def purchase_order_from_orm(obj: PurchaseOrderORM) -> PurchaseOrder:
    return PurchaseOrder(
        id=obj.id,
        organization_id=obj.organization_id,
        po_number=obj.po_number,
        site_id=obj.site_id,
        supplier_party_id=obj.supplier_party_id,
        status=PurchaseOrderStatus(obj.status),
        order_date=obj.order_date,
        expected_delivery_date=obj.expected_delivery_date,
        currency_code=obj.currency_code or "",
        approval_request_id=obj.approval_request_id,
        source_requisition_id=obj.source_requisition_id,
        supplier_reference=obj.supplier_reference or "",
        submitted_at=obj.submitted_at,
        approved_at=obj.approved_at,
        sent_at=obj.sent_at,
        closed_at=obj.closed_at,
        cancelled_at=obj.cancelled_at,
        notes=obj.notes or "",
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
    )


def purchase_order_line_to_orm(line: PurchaseOrderLine) -> PurchaseOrderLineORM:
    return PurchaseOrderLineORM(
        id=line.id,
        purchase_order_id=line.purchase_order_id,
        line_number=line.line_number,
        stock_item_id=line.stock_item_id,
        destination_storeroom_id=line.destination_storeroom_id,
        description=line.description or None,
        quantity_ordered=line.quantity_ordered,
        quantity_received=line.quantity_received,
        quantity_rejected=line.quantity_rejected,
        uom=line.uom,
        unit_price=line.unit_price,
        expected_delivery_date=line.expected_delivery_date,
        source_requisition_line_id=line.source_requisition_line_id,
        status=line.status,
        notes=line.notes or None,
    )


def purchase_order_line_from_orm(obj: PurchaseOrderLineORM) -> PurchaseOrderLine:
    return PurchaseOrderLine(
        id=obj.id,
        purchase_order_id=obj.purchase_order_id,
        line_number=obj.line_number,
        stock_item_id=obj.stock_item_id,
        destination_storeroom_id=obj.destination_storeroom_id,
        description=obj.description or "",
        quantity_ordered=float(obj.quantity_ordered or 0.0),
        quantity_received=float(obj.quantity_received or 0.0),
        quantity_rejected=float(obj.quantity_rejected or 0.0),
        uom=obj.uom,
        unit_price=float(obj.unit_price or 0.0),
        expected_delivery_date=obj.expected_delivery_date,
        source_requisition_line_id=obj.source_requisition_line_id,
        status=PurchaseOrderLineStatus(obj.status),
        notes=obj.notes or "",
    )


def receipt_header_to_orm(receipt: ReceiptHeader) -> ReceiptHeaderORM:
    return ReceiptHeaderORM(
        id=receipt.id,
        organization_id=receipt.organization_id,
        receipt_number=receipt.receipt_number,
        purchase_order_id=receipt.purchase_order_id,
        received_site_id=receipt.received_site_id,
        supplier_party_id=receipt.supplier_party_id,
        status=receipt.status,
        receipt_date=receipt.receipt_date,
        supplier_delivery_reference=receipt.supplier_delivery_reference or None,
        received_by_user_id=receipt.received_by_user_id,
        received_by_username=receipt.received_by_username or None,
        notes=receipt.notes or None,
        created_at=receipt.created_at,
    )


def receipt_header_from_orm(obj: ReceiptHeaderORM) -> ReceiptHeader:
    return ReceiptHeader(
        id=obj.id,
        organization_id=obj.organization_id,
        receipt_number=obj.receipt_number,
        purchase_order_id=obj.purchase_order_id,
        received_site_id=obj.received_site_id,
        supplier_party_id=obj.supplier_party_id,
        status=ReceiptStatus(obj.status),
        receipt_date=obj.receipt_date,
        supplier_delivery_reference=obj.supplier_delivery_reference or "",
        received_by_user_id=obj.received_by_user_id,
        received_by_username=obj.received_by_username or "",
        notes=obj.notes or "",
        created_at=obj.created_at,
    )


def receipt_line_to_orm(line: ReceiptLine) -> ReceiptLineORM:
    return ReceiptLineORM(
        id=line.id,
        receipt_header_id=line.receipt_header_id,
        purchase_order_line_id=line.purchase_order_line_id,
        line_number=line.line_number,
        stock_item_id=line.stock_item_id,
        storeroom_id=line.storeroom_id,
        quantity_accepted=line.quantity_accepted,
        quantity_rejected=line.quantity_rejected,
        uom=line.uom,
        unit_cost=line.unit_cost,
        lot_number=line.lot_number or None,
        serial_number=line.serial_number or None,
        expiry_date=line.expiry_date,
        notes=line.notes or None,
    )


def receipt_line_from_orm(obj: ReceiptLineORM) -> ReceiptLine:
    return ReceiptLine(
        id=obj.id,
        receipt_header_id=obj.receipt_header_id,
        purchase_order_line_id=obj.purchase_order_line_id,
        line_number=obj.line_number,
        stock_item_id=obj.stock_item_id,
        storeroom_id=obj.storeroom_id,
        quantity_accepted=float(obj.quantity_accepted or 0.0),
        quantity_rejected=float(obj.quantity_rejected or 0.0),
        uom=obj.uom,
        unit_cost=float(obj.unit_cost or 0.0),
        lot_number=obj.lot_number or "",
        serial_number=obj.serial_number or "",
        expiry_date=obj.expiry_date,
        notes=obj.notes or "",
    )


__all__ = [
    "purchase_order_from_orm",
    "purchase_order_line_from_orm",
    "purchase_order_line_to_orm",
    "purchase_order_to_orm",
    "purchase_requisition_from_orm",
    "purchase_requisition_line_from_orm",
    "purchase_requisition_line_to_orm",
    "purchase_requisition_to_orm",
    "receipt_header_from_orm",
    "receipt_header_to_orm",
    "receipt_line_from_orm",
    "receipt_line_to_orm",
]
