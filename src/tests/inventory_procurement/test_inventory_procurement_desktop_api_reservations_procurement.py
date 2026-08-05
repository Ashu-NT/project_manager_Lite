from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from src.api.desktop.runtime import build_desktop_api_registry
from src.core.modules.inventory_procurement.api.desktop import (
    InventoryAdjustmentCommand,
    InventoryCycleCountCreateCommand,
    InventoryLocationCreateCommand,
    InventoryCategoryCreateCommand,
    InventoryIssueCommand,
    InventoryItemCreateCommand,
    InventoryItemUpdateCommand,
    InventoryOpeningBalanceCommand,
    InventoryProcurementDashboardDesktopApi,
    InventoryProcurementPricingDesktopApi,
    InventoryReorderPolicyUpsertCommand,
    InventoryPurchaseOrderCreateCommand,
    InventoryPurchaseOrderLineCreateCommand,
    InventoryReceiptLineCommand,
    InventoryReceiptPostCommand,
    InventoryRequisitionCreateCommand,
    InventoryRequisitionLineCreateCommand,
    InventoryReservationCreateCommand,
    InventoryReservationIssueCommand,
    InventoryStoreroomCreateCommand,
    InventoryTransferCommand,
    build_inventory_procurement_catalog_desktop_api,
    build_inventory_procurement_dashboard_desktop_api,
    build_inventory_procurement_inventory_desktop_api,
    build_inventory_procurement_pricing_desktop_api,
    build_inventory_procurement_procurement_desktop_api,
    build_inventory_procurement_reservations_desktop_api,
    build_inventory_procurement_workspace_desktop_api,
)
from src.core.platform.domain.master_data.party import PartyType
from src.tests.ui_runtime_helpers import login_as


EXPECTED_INVENTORY_WORKSPACE_KEYS = [
    "dashboard",
    "catalog",
    "inventory",
    "reservations",
    "procurement",
    "pricing",
    "movements",
    "warehouses",
]


def _create_shared_inventory_references(services):
    site = services["site_service"].create_site(
        site_code="INV-HQ",
        name="Inventory HQ",
        city="Berlin",
        currency_code="EUR",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-INV",
        party_name="North Supply GmbH",
        party_type=PartyType.SUPPLIER,
    )
    manager = services["party_service"].create_party(
        party_code="CTR-INV",
        party_name="Managed Stores GmbH",
        party_type=PartyType.CONTRACTOR,
    )
    return site, supplier, manager


def _build_catalog_api(services):
    return build_inventory_procurement_catalog_desktop_api(
        category_service=services["inventory_item_category_service"],
        item_service=services["inventory_item_service"],
        reference_service=services["inventory_reference_service"],
    )


def _build_inventory_api(services):
    return build_inventory_procurement_inventory_desktop_api(
        inventory_service=services["inventory_service"],
        stock_service=services["inventory_stock_service"],
        item_service=services["inventory_item_service"],
        reference_service=services["inventory_reference_service"],
        foundation_service=services["inventory_foundation_service"],
        reservation_service=services["inventory_reservation_service"],
        procurement_service=services["inventory_procurement_service"],
        purchasing_service=services["inventory_purchasing_service"],
        reporting_service=services["inventory_reporting_service"],
        module_catalog_service=services["module_catalog_service"],
    )


def _build_reservations_api(services):
    return build_inventory_procurement_reservations_desktop_api(
        reservation_service=services["inventory_reservation_service"],
        item_service=services["inventory_item_service"],
        inventory_service=services["inventory_service"],
    )


def _build_procurement_api(services):
    return build_inventory_procurement_procurement_desktop_api(
        procurement_service=services["inventory_procurement_service"],
        purchasing_service=services["inventory_purchasing_service"],
        reference_service=services["inventory_reference_service"],
        inventory_service=services["inventory_service"],
        item_service=services["inventory_item_service"],
    )


def _build_dashboard_api(services) -> InventoryProcurementDashboardDesktopApi:
    return build_inventory_procurement_dashboard_desktop_api(
        item_service=services["inventory_item_service"],
        inventory_service=services["inventory_service"],
        stock_service=services["inventory_stock_service"],
        reservation_service=services["inventory_reservation_service"],
        procurement_service=services["inventory_procurement_service"],
        purchasing_service=services["inventory_purchasing_service"],
        reference_service=services["inventory_reference_service"],
    )


def _build_pricing_api(services) -> InventoryProcurementPricingDesktopApi:
    return build_inventory_procurement_pricing_desktop_api(
        reporting_service=services["inventory_reporting_service"],
        reference_service=services["inventory_reference_service"],
        inventory_service=services["inventory_service"],
        purchasing_service=services["inventory_purchasing_service"],
        item_service=services["inventory_item_service"],
        user_session=services["user_session"],
    )


def test_inventory_reservations_desktop_api_manages_reservation_flows(services) -> None:
    site, _, _ = _create_shared_inventory_references(services)
    catalog_api = _build_catalog_api(services)
    inventory_api = _build_inventory_api(services)
    reservations_api = _build_reservations_api(services)

    item = catalog_api.create_item(
        InventoryItemCreateCommand(
            item_code="GSK-001",
            name="Seal Gasket",
            status="ACTIVE",
            stock_uom="EA",
        )
    )
    storeroom = inventory_api.create_storeroom(
        InventoryStoreroomCreateCommand(
            storeroom_code="RES-MAIN",
            name="Reservation Main",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
        )
    )
    inventory_api.post_opening_balance(
        InventoryOpeningBalanceCommand(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=50,
            uom="EA",
        )
    )

    reservation = reservations_api.create_reservation(
        InventoryReservationCreateCommand(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            reserved_qty=12,
            uom="EA",
            source_reference_type="task",
            source_reference_id="task-42",
        )
    )
    issued = reservations_api.issue_reserved_stock(
        InventoryReservationIssueCommand(
            reservation_id=reservation.id,
            quantity=5,
            note="Issued to crew",
        )
    )
    released = reservations_api.release_reservation(issued.id, note="Close remaining")

    assert reservation.status == "ACTIVE"
    assert issued.status == "PARTIALLY_ISSUED"
    assert issued.remaining_qty == 7.0
    assert released.status == "RELEASED"


def test_inventory_procurement_desktop_api_manages_requisition_purchase_order_and_receipt_flows(services) -> None:
    services["auth_service"].register_user("inventory-api-buyer", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user("inventory-api-approver", "StrongPass123", role_names=["approver"])
    site, supplier, _ = _create_shared_inventory_references(services)
    catalog_api = _build_catalog_api(services)
    inventory_api = _build_inventory_api(services)
    procurement_api = _build_procurement_api(services)
    approvals = services["approval_service"]

    login_as(services, "inventory-api-buyer", "StrongPass123")

    item = catalog_api.create_item(
        InventoryItemCreateCommand(
            item_code="MTR-001",
            name="Electric Motor",
            status="ACTIVE",
            stock_uom="EA",
            is_purchase_allowed=True,
        )
    )
    storeroom = inventory_api.create_storeroom(
        InventoryStoreroomCreateCommand(
            storeroom_code="PROC-MAIN",
            name="Procurement Main",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
        )
    )

    requisition = procurement_api.create_requisition(
        InventoryRequisitionCreateCommand(
            requesting_site_id=site.id,
            requesting_storeroom_id=storeroom.id,
            purpose="Motor replacement",
            needed_by_date=date(2026, 5, 20),
        )
    )
    req_line = procurement_api.add_requisition_line(
        InventoryRequisitionLineCreateCommand(
            requisition_id=requisition.id,
            stock_item_id=item.id,
            quantity_requested=2,
            uom="EA",
            estimated_unit_cost=550.0,
            suggested_supplier_party_id=supplier.id,
        )
    )
    requisition = procurement_api.submit_requisition(requisition.id, note="Submit for sourcing")
    login_as(services, "inventory-api-approver", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved requisition")

    login_as(services, "inventory-api-buyer", "StrongPass123")
    purchase_order = procurement_api.create_purchase_order(
        InventoryPurchaseOrderCreateCommand(
            site_id=site.id,
            supplier_party_id=supplier.id,
            source_requisition_id=requisition.id,
            expected_delivery_date=date(2026, 5, 25),
            supplier_reference="SUP-PO-001",
        )
    )
    po_line = procurement_api.add_purchase_order_line(
        InventoryPurchaseOrderLineCreateCommand(
            purchase_order_id=purchase_order.id,
            stock_item_id=item.id,
            destination_storeroom_id=storeroom.id,
            quantity_ordered=2,
            uom="EA",
            unit_price=525.0,
            source_requisition_line_id=req_line.id,
        )
    )
    purchase_order = procurement_api.submit_purchase_order(purchase_order.id, note="Submit PO")
    login_as(services, "inventory-api-approver", "StrongPass123")
    approvals.approve_and_apply(purchase_order.approval_request_id, note="Approved PO")
    login_as(services, "inventory-api-buyer", "StrongPass123")
    purchase_order = procurement_api.send_purchase_order(purchase_order.id, note="Sent to supplier")
    receipt = procurement_api.post_receipt(
        InventoryReceiptPostCommand(
            purchase_order_id=purchase_order.id,
            receipt_lines=(
                InventoryReceiptLineCommand(
                    purchase_order_line_id=po_line.id,
                    quantity_accepted=2,
                    unit_cost=525.0,
                ),
            ),
            supplier_delivery_reference="DN-1001",
        )
    )

    receipts = procurement_api.list_receipts(purchase_order_id=purchase_order.id)
    receipt_lines = procurement_api.list_receipt_lines(receipt.id)

    assert requisition.status == "SUBMITTED"
    assert purchase_order.status == "SENT"
    assert receipts[0].receipt_number == receipt.receipt_number
    assert receipt_lines[0].quantity_accepted == 2.0
