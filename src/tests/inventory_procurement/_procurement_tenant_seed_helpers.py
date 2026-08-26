from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrderLine,
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
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
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.catalog import (
    SqlAlchemyInventoryItemCategoryRepository,
    SqlAlchemyStockItemRepository,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.inventory import (
    SqlAlchemyCycleCountRepository,
    SqlAlchemyReorderPolicyRepository,
    SqlAlchemyStockBalanceRepository,
    SqlAlchemyStockReservationRepository,
    SqlAlchemyStockTransactionRepository,
    SqlAlchemyStorageLocationRepository,
    SqlAlchemyStoreroomRepository,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseOrderLineRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemyPurchaseRequisitionLineRepository,
    SqlAlchemyPurchaseRequisitionRepository,
    SqlAlchemyReceiptHeaderRepository,
    SqlAlchemyReceiptLineRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.master_data.party import PartyType


def _inventory_repo(repo_factory, services):
    return repo_factory(
        services["session"],
        tenant_context_service=services["tenant_context_service"],
    )


def _seed_inventory_scope_rows(services) -> dict[str, str]:
    organization_service = services["organization_service"]
    current_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="INV-TENANT-OPS",
        display_name="Inventory Tenant Operations",
        timezone_name="UTC",
        base_currency="USD",
        is_enabled=False,
    )

    assert current_org is not None
    assert other_org is not None

    category_service = services["inventory_item_category_service"]
    item_service = services["inventory_item_service"]
    inventory_service = services["inventory_service"]
    stock_service = services["inventory_stock_service"]
    foundation_service = services["inventory_foundation_service"]
    site_service = services["site_service"]

    def build_rows(prefix: str) -> dict[str, str]:
        site = site_service.create_site(
            site_code=f"{prefix}-SITE",
            name=f"{prefix} Site",
            city="Berlin",
            currency_code="EUR",
        )
        category = category_service.create_category(
            category_code=f"{prefix}-CAT",
            name=f"{prefix} Category",
            category_type="SPARE",
        )
        item = item_service.create_item(
            item_code=f"{prefix}-ITEM",
            name=f"{prefix} Item",
            status="ACTIVE",
            stock_uom="EA",
            category_code=category.category_code,
        )
        storeroom = inventory_service.create_storeroom(
            storeroom_code=f"{prefix}-STORE",
            name=f"{prefix} Storeroom",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
        )
        stock_service.post_opening_balance(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=10,
            uom="EA",
            unit_cost=5.0,
        )
        balance = stock_service.get_balance_for_stock_position(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
        )
        transactions = stock_service.list_transactions(limit=20)
        location = foundation_service.create_storage_location(
            storeroom_id=storeroom.id,
            location_code=f"{prefix}-BIN",
            name=f"{prefix} Bin",
            location_type="BIN",
        )
        policy = foundation_service.upsert_reorder_policy(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            location_id=location.id,
            policy_name=f"{prefix} Policy",
            min_qty=2,
            max_qty=10,
            reorder_point=4,
            reorder_qty=6,
        )
        cycle_count = foundation_service.schedule_cycle_count(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            location_id=location.id,
            scheduled_count_date="2026-06-01",
            notes=f"{prefix} count",
        )

        assert balance is not None
        assert transactions

        transaction = transactions[0]
        return {
            "category_id": category.id,
            "category_code": category.category_code,
            "item_id": item.id,
            "item_code": item.item_code,
            "storeroom_id": storeroom.id,
            "storeroom_code": storeroom.storeroom_code,
            "balance_id": balance.id,
            "transaction_id": transaction.id,
            "transaction_number": transaction.transaction_number,
            "location_id": location.id,
            "location_code": location.location_code,
            "policy_id": policy.id,
            "cycle_count_id": cycle_count.id,
            "cycle_count_number": cycle_count.cycle_count_number,
        }

    current_rows = build_rows("CUR")
    organization_service.enable_organization(other_org.id)
    tenant_context_service.set_active_organization(other_org.id)
    other_rows = build_rows("OTH")
    organization_service.enable_organization(current_org.id)
    tenant_context_service.set_active_organization(current_org.id)

    return {
        "current_org_id": current_org.id,
        "other_org_id": other_org.id,
        "current_category_id": current_rows["category_id"],
        "current_category_code": current_rows["category_code"],
        "current_item_id": current_rows["item_id"],
        "current_item_code": current_rows["item_code"],
        "current_storeroom_id": current_rows["storeroom_id"],
        "current_storeroom_code": current_rows["storeroom_code"],
        "current_balance_id": current_rows["balance_id"],
        "current_transaction_id": current_rows["transaction_id"],
        "current_transaction_number": current_rows["transaction_number"],
        "current_location_id": current_rows["location_id"],
        "current_location_code": current_rows["location_code"],
        "current_policy_id": current_rows["policy_id"],
        "current_cycle_count_id": current_rows["cycle_count_id"],
        "current_cycle_count_number": current_rows["cycle_count_number"],
        "other_category_id": other_rows["category_id"],
        "other_category_code": other_rows["category_code"],
        "other_item_id": other_rows["item_id"],
        "other_item_code": other_rows["item_code"],
        "other_storeroom_id": other_rows["storeroom_id"],
        "other_storeroom_code": other_rows["storeroom_code"],
        "other_balance_id": other_rows["balance_id"],
        "other_transaction_id": other_rows["transaction_id"],
        "other_transaction_number": other_rows["transaction_number"],
        "other_location_id": other_rows["location_id"],
        "other_location_code": other_rows["location_code"],
        "other_policy_id": other_rows["policy_id"],
        "other_cycle_count_id": other_rows["cycle_count_id"],
        "other_cycle_count_number": other_rows["cycle_count_number"],
    }


def _seed_procurement_scope_rows(services) -> dict[str, str]:
    session = services["session"]
    organization_service = services["organization_service"]
    current_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="PROC-TENANT-OPS",
        display_name="Procurement Tenant Operations",
        timezone_name="UTC",
        base_currency="USD",
        is_enabled=False,
    )

    assert current_org is not None
    assert other_org is not None

    site_service = services["site_service"]
    item_service = services["inventory_item_service"]
    inventory_service = services["inventory_service"]
    party_service = services["party_service"]

    current_tenant_id = getattr(current_org, "tenant_id", None)
    other_tenant_id = getattr(other_org, "tenant_id", None) or current_tenant_id
    now = datetime.now(timezone.utc)

    def build_reference_rows(prefix: str) -> dict[str, str]:
        site = site_service.create_site(
            site_code=f"{prefix}-PROC-SITE",
            name=f"{prefix} Procurement Site",
            city="Berlin",
            currency_code="EUR",
        )
        item = item_service.create_item(
            item_code=f"{prefix}-PROC-ITEM",
            name=f"{prefix} Procurement Item",
            status="ACTIVE",
            stock_uom="EA",
            is_purchase_allowed=True,
        )
        storeroom = inventory_service.create_storeroom(
            storeroom_code=f"{prefix}-PROC-STORE",
            name=f"{prefix} Procurement Storeroom",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
        )
        supplier = party_service.create_party(
            party_code=f"{prefix}-PROC-SUP",
            party_name=f"{prefix} Procurement Supplier",
            party_type=PartyType.SUPPLIER,
        )
        return {
            "site_id": site.id,
            "item_id": item.id,
            "storeroom_id": storeroom.id,
            "supplier_id": supplier.id,
        }

    current_refs = build_reference_rows("CUR")
    organization_service.enable_organization(other_org.id)
    tenant_context_service.set_active_organization(other_org.id)
    other_refs = build_reference_rows("OTH")
    organization_service.enable_organization(current_org.id)
    tenant_context_service.set_active_organization(current_org.id)

    current_requisition = PurchaseRequisitionORM(
        id="req-current-scope",
        tenant_id=current_tenant_id,
        organization_id=current_org.id,
        requisition_number="REQ-CUR-SCOPE",
        requesting_site_id=current_refs["site_id"],
        requesting_storeroom_id=current_refs["storeroom_id"],
        requester_user_id=None,
        requester_username="scope-user",
        status=PurchaseRequisitionStatus.APPROVED,
        purpose="Current scope requisition",
        needed_by_date=None,
        priority="NORMAL",
        approval_request_id=None,
        source_reference_type=None,
        source_reference_id=None,
        source_module=None,
        source_entity_type=None,
        source_code_snapshot=None,
        source_title_snapshot=None,
        source_status_snapshot=None,
        submitted_at=now,
        approved_at=now,
        cancelled_at=None,
        notes="Current requisition",
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_requisition = PurchaseRequisitionORM(
        id="req-other-scope",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        requisition_number="REQ-OTH-SCOPE",
        requesting_site_id=other_refs["site_id"],
        requesting_storeroom_id=other_refs["storeroom_id"],
        requester_user_id=None,
        requester_username="scope-user",
        status=PurchaseRequisitionStatus.APPROVED,
        purpose="Other scope requisition",
        needed_by_date=None,
        priority="NORMAL",
        approval_request_id=None,
        source_reference_type=None,
        source_reference_id=None,
        source_module=None,
        source_entity_type=None,
        source_code_snapshot=None,
        source_title_snapshot=None,
        source_status_snapshot=None,
        submitted_at=now,
        approved_at=now,
        cancelled_at=None,
        notes="Other requisition",
        created_at=now,
        updated_at=now,
        version=1,
    )
    current_requisition_line = PurchaseRequisitionLineORM(
        id="req-line-current-scope",
        purchase_requisition_id=current_requisition.id,
        line_number=1,
        stock_item_id=current_refs["item_id"],
        description="Current requisition line",
        quantity_requested=5.0,
        uom="EA",
        needed_by_date=None,
        estimated_unit_cost=10.0,
        quantity_sourced=2.0,
        suggested_supplier_party_id=current_refs["supplier_id"],
        status=PurchaseRequisitionLineStatus.PARTIALLY_SOURCED,
        notes="Current requisition line",
    )
    other_requisition_line = PurchaseRequisitionLineORM(
        id="req-line-other-scope",
        purchase_requisition_id=other_requisition.id,
        line_number=1,
        stock_item_id=other_refs["item_id"],
        description="Other requisition line",
        quantity_requested=4.0,
        uom="EA",
        needed_by_date=None,
        estimated_unit_cost=12.0,
        quantity_sourced=1.0,
        suggested_supplier_party_id=other_refs["supplier_id"],
        status=PurchaseRequisitionLineStatus.PARTIALLY_SOURCED,
        notes="Other requisition line",
    )
    current_purchase_order = PurchaseOrderORM(
        id="po-current-scope",
        tenant_id=current_tenant_id,
        organization_id=current_org.id,
        po_number="PO-CUR-SCOPE",
        site_id=current_refs["site_id"],
        supplier_party_id=current_refs["supplier_id"],
        status=PurchaseOrderStatus.APPROVED,
        order_date=now.date(),
        expected_delivery_date=now.date(),
        currency_code="EUR",
        approval_request_id=None,
        source_requisition_id=current_requisition.id,
        supplier_reference="SUP-CUR",
        submitted_at=now,
        approved_at=now,
        sent_at=None,
        closed_at=None,
        cancelled_at=None,
        notes="Current purchase order",
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_purchase_order = PurchaseOrderORM(
        id="po-other-scope",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        po_number="PO-OTH-SCOPE",
        site_id=other_refs["site_id"],
        supplier_party_id=other_refs["supplier_id"],
        status=PurchaseOrderStatus.APPROVED,
        order_date=now.date(),
        expected_delivery_date=now.date(),
        currency_code="EUR",
        approval_request_id=None,
        source_requisition_id=other_requisition.id,
        supplier_reference="SUP-OTH",
        submitted_at=now,
        approved_at=now,
        sent_at=None,
        closed_at=None,
        cancelled_at=None,
        notes="Other purchase order",
        created_at=now,
        updated_at=now,
        version=1,
    )
    current_purchase_order_line = PurchaseOrderLineORM(
        id="po-line-current-scope",
        purchase_order_id=current_purchase_order.id,
        line_number=1,
        stock_item_id=current_refs["item_id"],
        destination_storeroom_id=current_refs["storeroom_id"],
        description="Current purchase order line",
        quantity_ordered=3.0,
        quantity_received=1.0,
        quantity_rejected=0.0,
        uom="EA",
        unit_price=9.5,
        expected_delivery_date=now.date(),
        source_requisition_line_id=current_requisition_line.id,
        status=PurchaseOrderLineStatus.PARTIALLY_RECEIVED,
        notes="Current purchase order line",
    )
    other_purchase_order_line = PurchaseOrderLineORM(
        id="po-line-other-scope",
        purchase_order_id=other_purchase_order.id,
        line_number=1,
        stock_item_id=other_refs["item_id"],
        destination_storeroom_id=other_refs["storeroom_id"],
        description="Other purchase order line",
        quantity_ordered=2.0,
        quantity_received=0.0,
        quantity_rejected=0.0,
        uom="EA",
        unit_price=11.0,
        expected_delivery_date=now.date(),
        source_requisition_line_id=other_requisition_line.id,
        status=PurchaseOrderLineStatus.OPEN,
        notes="Other purchase order line",
    )
    current_receipt = ReceiptHeaderORM(
        id="receipt-current-scope",
        tenant_id=current_tenant_id,
        organization_id=current_org.id,
        receipt_number="RCV-CUR-SCOPE",
        purchase_order_id=current_purchase_order.id,
        received_site_id=current_refs["site_id"],
        supplier_party_id=current_refs["supplier_id"],
        status=ReceiptStatus.POSTED,
        receipt_date=now,
        supplier_delivery_reference="DEL-CUR",
        received_by_user_id=None,
        received_by_username="scope-user",
        notes="Current receipt",
        created_at=now,
    )
    other_receipt = ReceiptHeaderORM(
        id="receipt-other-scope",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        receipt_number="RCV-OTH-SCOPE",
        purchase_order_id=other_purchase_order.id,
        received_site_id=other_refs["site_id"],
        supplier_party_id=other_refs["supplier_id"],
        status=ReceiptStatus.POSTED,
        receipt_date=now,
        supplier_delivery_reference="DEL-OTH",
        received_by_user_id=None,
        received_by_username="scope-user",
        notes="Other receipt",
        created_at=now,
    )
    current_receipt_line = ReceiptLineORM(
        id="receipt-line-current-scope",
        receipt_header_id=current_receipt.id,
        purchase_order_line_id=current_purchase_order_line.id,
        line_number=1,
        stock_item_id=current_refs["item_id"],
        storeroom_id=current_refs["storeroom_id"],
        quantity_accepted=1.0,
        quantity_rejected=0.0,
        uom="EA",
        unit_cost=9.5,
        lot_number=None,
        serial_number=None,
        expiry_date=None,
        notes="Current receipt line",
    )
    other_receipt_line = ReceiptLineORM(
        id="receipt-line-other-scope",
        receipt_header_id=other_receipt.id,
        purchase_order_line_id=other_purchase_order_line.id,
        line_number=1,
        stock_item_id=other_refs["item_id"],
        storeroom_id=other_refs["storeroom_id"],
        quantity_accepted=1.0,
        quantity_rejected=0.0,
        uom="EA",
        unit_cost=11.0,
        lot_number=None,
        serial_number=None,
        expiry_date=None,
        notes="Other receipt line",
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
