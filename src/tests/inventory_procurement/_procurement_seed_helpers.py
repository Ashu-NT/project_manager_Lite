from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
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
from src.core.platform.party.domain import PartyType


def _seed_procurement_scope_rows(services) -> dict[str, str]:
    session = services["session"]
    organization_service = services["organization_service"]
    current_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="PROC-TENANT-OPS",
        display_name="Procurement Tenant Operations",
        timezone_name="UTC", base_currency="USD", is_active=False,
    )
    site_service = services["site_service"]
    item_service = services["inventory_item_service"]
    inventory_service = services["inventory_service"]
    party_service = services["party_service"]
    current_tenant_id = getattr(current_org, "tenant_id", None)
    other_tenant_id = getattr(other_org, "tenant_id", None) or current_tenant_id
    now = datetime.now(timezone.utc)

    def build_reference_rows(prefix: str) -> dict[str, str]:
        site = site_service.create_site(
            site_code=f"{prefix}-PROC-SITE", name=f"{prefix} Procurement Site",
            city="Berlin", currency_code="EUR",
        )
        item = item_service.create_item(
            item_code=f"{prefix}-PROC-ITEM", name=f"{prefix} Procurement Item",
            status="ACTIVE", stock_uom="EA", is_purchase_allowed=True,
        )
        storeroom = inventory_service.create_storeroom(
            storeroom_code=f"{prefix}-PROC-STORE", name=f"{prefix} Procurement Storeroom",
            site_id=site.id, status="ACTIVE", storeroom_type="MAIN",
        )
        supplier = party_service.create_party(
            party_code=f"{prefix}-PROC-SUP", party_name=f"{prefix} Procurement Supplier",
            party_type=PartyType.SUPPLIER,
        )
        return {"site_id": site.id, "item_id": item.id, "storeroom_id": storeroom.id, "supplier_id": supplier.id}

    current_refs = build_reference_rows("CUR")
    organization_service.set_active_organization(other_org.id)
    other_refs = build_reference_rows("OTH")
    organization_service.set_active_organization(current_org.id)

    current_requisition = PurchaseRequisitionORM(
        id="req-current-scope", tenant_id=current_tenant_id,
        organization_id=current_org.id, requisition_number="REQ-CUR-SCOPE",
        requesting_site_id=current_refs["site_id"],
        requesting_storeroom_id=current_refs["storeroom_id"],
        requester_user_id=None, requester_username="scope-user",
        status=PurchaseRequisitionStatus.APPROVED, purpose="Current scope requisition",
        needed_by_date=None, priority="NORMAL", approval_request_id=None,
        source_reference_type=None, source_reference_id=None, source_module=None,
        source_entity_type=None, source_code_snapshot=None,
        source_title_snapshot=None, source_status_snapshot=None,
        submitted_at=now, approved_at=now, cancelled_at=None,
        notes="Current requisition", created_at=now, updated_at=now, version=1,
    )
    other_requisition = PurchaseRequisitionORM(
        id="req-other-scope", tenant_id=other_tenant_id,
        organization_id=other_org.id, requisition_number="REQ-OTH-SCOPE",
        requesting_site_id=other_refs["site_id"],
        requesting_storeroom_id=other_refs["storeroom_id"],
        requester_user_id=None, requester_username="scope-user",
        status=PurchaseRequisitionStatus.APPROVED, purpose="Other scope requisition",
        needed_by_date=None, priority="NORMAL", approval_request_id=None,
        source_reference_type=None, source_reference_id=None, source_module=None,
        source_entity_type=None, source_code_snapshot=None,
        source_title_snapshot=None, source_status_snapshot=None,
        submitted_at=now, approved_at=now, cancelled_at=None,
        notes="Other requisition", created_at=now, updated_at=now, version=1,
    )
    current_requisition_line = PurchaseRequisitionLineORM(
        id="req-line-current-scope", purchase_requisition_id=current_requisition.id,
        line_number=1, stock_item_id=current_refs["item_id"],
        description="Current requisition line", quantity_requested=5.0, uom="EA",
        needed_by_date=None, estimated_unit_cost=10.0, quantity_sourced=2.0,
        suggested_supplier_party_id=current_refs["supplier_id"],
        status=PurchaseRequisitionLineStatus.PARTIALLY_SOURCED, notes="Current requisition line",
    )
    other_requisition_line = PurchaseRequisitionLineORM(
        id="req-line-other-scope", purchase_requisition_id=other_requisition.id,
        line_number=1, stock_item_id=other_refs["item_id"],
        description="Other requisition line", quantity_requested=4.0, uom="EA",
        needed_by_date=None, estimated_unit_cost=12.0, quantity_sourced=1.0,
        suggested_supplier_party_id=other_refs["supplier_id"],
        status=PurchaseRequisitionLineStatus.PARTIALLY_SOURCED, notes="Other requisition line",
    )
    current_purchase_order = PurchaseOrderORM(
        id="po-current-scope", tenant_id=current_tenant_id,
        organization_id=current_org.id, po_number="PO-CUR-SCOPE",
        site_id=current_refs["site_id"], supplier_party_id=current_refs["supplier_id"],
        status=PurchaseOrderStatus.APPROVED, order_date=now.date(),
        expected_delivery_date=now.date(), currency_code="EUR",
        approval_request_id=None, source_requisition_id=current_requisition.id,
        supplier_reference="SUP-CUR", submitted_at=now, approved_at=now,
        sent_at=None, closed_at=None, cancelled_at=None,
        notes="Current purchase order", created_at=now, updated_at=now, version=1,
    )
    other_purchase_order = PurchaseOrderORM(
        id="po-other-scope", tenant_id=other_tenant_id,
        organization_id=other_org.id, po_number="PO-OTH-SCOPE",
        site_id=other_refs["site_id"], supplier_party_id=other_refs["supplier_id"],
        status=PurchaseOrderStatus.APPROVED, order_date=now.date(),
        expected_delivery_date=now.date(), currency_code="EUR",
        approval_request_id=None, source_requisition_id=other_requisition.id,
        supplier_reference="SUP-OTH", submitted_at=now, approved_at=now,
        sent_at=None, closed_at=None, cancelled_at=None,
        notes="Other purchase order", created_at=now, updated_at=now, version=1,
    )
    current_purchase_order_line = PurchaseOrderLineORM(
        id="po-line-current-scope", purchase_order_id=current_purchase_order.id,
        line_number=1, stock_item_id=current_refs["item_id"],
        destination_storeroom_id=current_refs["storeroom_id"],
        description="Current purchase order line", quantity_ordered=3.0,
        quantity_received=1.0, quantity_rejected=0.0, uom="EA", unit_price=9.5,
        expected_delivery_date=now.date(),
        source_requisition_line_id=current_requisition_line.id,
        status=PurchaseOrderLineStatus.PARTIALLY_RECEIVED, notes="Current purchase order line",
    )
    other_purchase_order_line = PurchaseOrderLineORM(
        id="po-line-other-scope", purchase_order_id=other_purchase_order.id,
        line_number=1, stock_item_id=other_refs["item_id"],
        destination_storeroom_id=other_refs["storeroom_id"],
        description="Other purchase order line", quantity_ordered=2.0,
        quantity_received=0.0, quantity_rejected=0.0, uom="EA", unit_price=11.0,
        expected_delivery_date=now.date(),
        source_requisition_line_id=other_requisition_line.id,
        status=PurchaseOrderLineStatus.OPEN, notes="Other purchase order line",
    )
    current_receipt = ReceiptHeaderORM(
        id="receipt-current-scope", tenant_id=current_tenant_id,
        organization_id=current_org.id, receipt_number="RCV-CUR-SCOPE",
        purchase_order_id=current_purchase_order.id,
        received_site_id=current_refs["site_id"], supplier_party_id=current_refs["supplier_id"],
        status=ReceiptStatus.POSTED, receipt_date=now,
        supplier_delivery_reference="DEL-CUR", received_by_user_id=None,
        received_by_username="scope-user", notes="Current receipt", created_at=now,
    )
    other_receipt = ReceiptHeaderORM(
        id="receipt-other-scope", tenant_id=other_tenant_id,
        organization_id=other_org.id, receipt_number="RCV-OTH-SCOPE",
        purchase_order_id=other_purchase_order.id,
        received_site_id=other_refs["site_id"], supplier_party_id=other_refs["supplier_id"],
        status=ReceiptStatus.POSTED, receipt_date=now,
        supplier_delivery_reference="DEL-OTH", received_by_user_id=None,
        received_by_username="scope-user", notes="Other receipt", created_at=now,
    )
    current_receipt_line = ReceiptLineORM(
        id="receipt-line-current-scope", receipt_header_id=current_receipt.id,
        purchase_order_line_id=current_purchase_order_line.id, line_number=1,
        stock_item_id=current_refs["item_id"], storeroom_id=current_refs["storeroom_id"],
        quantity_accepted=1.0, quantity_rejected=0.0, uom="EA", unit_cost=9.5,
        lot_number=None, serial_number=None, expiry_date=None, notes="Current receipt line",
    )
    other_receipt_line = ReceiptLineORM(
        id="receipt-line-other-scope", receipt_header_id=other_receipt.id,
        purchase_order_line_id=other_purchase_order_line.id, line_number=1,
        stock_item_id=other_refs["item_id"], storeroom_id=other_refs["storeroom_id"],
        quantity_accepted=1.0, quantity_rejected=0.0, uom="EA", unit_cost=11.0,
        lot_number=None, serial_number=None, expiry_date=None, notes="Other receipt line",
    )

    session.add_all([current_requisition, other_requisition])
    session.flush()
    session.add_all([current_purchase_order, other_purchase_order])
    session.flush()
    session.add_all([current_receipt, other_receipt])
    session.flush()
    session.add_all([current_requisition_line, other_requisition_line])
    session.flush()
    session.add_all([current_purchase_order_line, other_purchase_order_line])
    session.flush()
    session.add_all([current_receipt_line, other_receipt_line])
    session.flush()

    return {
        "current_org_id": current_org.id,
        "other_org_id": other_org.id,
        "current_requisition_id": current_requisition.id,
        "other_requisition_id": other_requisition.id,
        "current_requisition_number": current_requisition.requisition_number,
        "other_requisition_number": other_requisition.requisition_number,
        "current_requisition_line_id": current_requisition_line.id,
        "other_requisition_line_id": other_requisition_line.id,
        "current_purchase_order_id": current_purchase_order.id,
        "other_purchase_order_id": other_purchase_order.id,
        "current_purchase_order_number": current_purchase_order.po_number,
        "other_purchase_order_number": other_purchase_order.po_number,
        "current_purchase_order_line_id": current_purchase_order_line.id,
        "other_purchase_order_line_id": other_purchase_order_line.id,
        "current_receipt_id": current_receipt.id,
        "other_receipt_id": other_receipt.id,
        "current_receipt_number": current_receipt.receipt_number,
        "other_receipt_number": other_receipt.receipt_number,
        "current_receipt_line_id": current_receipt_line.id,
        "other_receipt_line_id": other_receipt_line.id,
        "current_item_id": current_refs["item_id"],
        "other_item_id": other_refs["item_id"],
        "current_storeroom_id": current_refs["storeroom_id"],
        "other_storeroom_id": other_refs["storeroom_id"],
    }
