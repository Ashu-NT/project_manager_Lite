from __future__ import annotations

from datetime import date
from pathlib import Path

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryItemCreateCommand,
    InventoryOpeningBalanceCommand,
    InventoryPurchaseOrderCreateCommand,
    InventoryPurchaseOrderLineCreateCommand,
    InventoryReceiptLineCommand,
    InventoryReceiptPostCommand,
    InventoryRequisitionCreateCommand,
    InventoryRequisitionLineCreateCommand,
    InventoryStoreroomCreateCommand,
)
from src.tests.ui_runtime_helpers import login_as
from src.tests.inventory_procurement._inv_procurement_api_helpers import (
    _build_catalog_api,
    _build_inventory_api,
    _build_pricing_api,
    _build_procurement_api,
    _create_shared_inventory_references,
)


def test_inventory_pricing_desktop_api_builds_snapshot_and_exports_reports(
    services,
    tmp_path,
) -> None:
    active_organization_id = services["organization_service"].get_active_organization().id
    services["module_catalog_service"].license_module(active_organization_id, "inventory_procurement")
    services["module_catalog_service"].enable_module(active_organization_id, "inventory_procurement")
    services["auth_service"].register_user(
        "inventory-api-pricing-buyer",
        "StrongPass123",
        role_names=["inventory_manager"],
    )
    services["auth_service"].register_user(
        "inventory-api-pricing-approver",
        "StrongPass123",
        role_names=["approver"],
    )
    site, supplier, _ = _create_shared_inventory_references(services)
    catalog_api = _build_catalog_api(services)
    inventory_api = _build_inventory_api(services)
    procurement_api = _build_procurement_api(services)
    pricing_api = _build_pricing_api(services)
    approvals = services["approval_service"]

    login_as(services, "inventory-api-pricing-buyer", "StrongPass123")
    item = catalog_api.create_item(
        InventoryItemCreateCommand(
            item_code="PRC-001",
            name="Pricing Valve",
            status="ACTIVE",
            stock_uom="EA",
            reorder_point=3,
            reorder_qty=6,
            max_qty=12,
            is_purchase_allowed=True,
        )
    )
    storeroom = inventory_api.create_storeroom(
        InventoryStoreroomCreateCommand(
            storeroom_code="PRICE-MAIN",
            name="Pricing Main",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
        )
    )
    inventory_api.post_opening_balance(
        InventoryOpeningBalanceCommand(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=2,
            uom="EA",
            unit_cost=18.5,
        )
    )
    requisition = procurement_api.create_requisition(
        InventoryRequisitionCreateCommand(
            requesting_site_id=site.id,
            requesting_storeroom_id=storeroom.id,
            purpose="Pricing replenishment demand",
            needed_by_date=date(2026, 6, 1),
        )
    )
    requisition_line = procurement_api.add_requisition_line(
        InventoryRequisitionLineCreateCommand(
            requisition_id=requisition.id,
            stock_item_id=item.id,
            quantity_requested=4,
            uom="EA",
            estimated_unit_cost=20.0,
            suggested_supplier_party_id=supplier.id,
        )
    )
    requisition = procurement_api.submit_requisition(requisition.id, note="Queue pricing demand")
    login_as(services, "inventory-api-pricing-approver", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved pricing requisition")

    login_as(services, "inventory-api-pricing-buyer", "StrongPass123")
    purchase_order = procurement_api.create_purchase_order(
        InventoryPurchaseOrderCreateCommand(
            site_id=site.id,
            supplier_party_id=supplier.id,
            source_requisition_id=requisition.id,
            currency_code="EUR",
            expected_delivery_date=date(2026, 6, 5),
            supplier_reference="PRICE-PO-01",
        )
    )
    po_line = procurement_api.add_purchase_order_line(
        InventoryPurchaseOrderLineCreateCommand(
            purchase_order_id=purchase_order.id,
            stock_item_id=item.id,
            destination_storeroom_id=storeroom.id,
            quantity_ordered=4,
            uom="EA",
            unit_price=19.75,
            source_requisition_line_id=requisition_line.id,
        )
    )
    purchase_order = procurement_api.submit_purchase_order(purchase_order.id, note="Submit pricing PO")
    login_as(services, "inventory-api-pricing-approver", "StrongPass123")
    approvals.approve_and_apply(purchase_order.approval_request_id, note="Approved pricing PO")
    login_as(services, "inventory-api-pricing-buyer", "StrongPass123")
    procurement_api.send_purchase_order(purchase_order.id, note="Sent pricing PO")
    procurement_api.post_receipt(
        InventoryReceiptPostCommand(
            purchase_order_id=purchase_order.id,
            receipt_lines=(
                InventoryReceiptLineCommand(
                    purchase_order_line_id=po_line.id,
                    quantity_accepted=4,
                    unit_cost=19.75,
                ),
            ),
            supplier_delivery_reference="PRICE-DN-01",
        )
    )

    snapshot = pricing_api.build_snapshot(
        site_id=site.id,
        storeroom_id=storeroom.id,
        supplier_party_id=supplier.id,
        limit=200,
    )
    stock_csv = pricing_api.export_stock_status_csv(
        str(tmp_path / "pricing-stock"),
        site_id=site.id,
        storeroom_id=storeroom.id,
    )
    procurement_excel = pricing_api.export_procurement_overview_excel(
        str(tmp_path / "pricing-procurement"),
        site_id=site.id,
        storeroom_id=storeroom.id,
        supplier_party_id=supplier.id,
        limit=200,
    )

    metric_by_label = {metric.label: metric for metric in snapshot.metrics}

    assert snapshot.title == "Pricing"
    assert snapshot.can_export is True
    assert snapshot.stock_rows[0].title.startswith("PRC-001")
    assert snapshot.supplier_price_rows[0].status_label.startswith("EUR")
    assert metric_by_label["Purchase Orders"].value == "1"
    assert metric_by_label["Receipts"].value == "1"
    assert stock_csv.endswith(".csv")
    assert Path(stock_csv).exists()
    assert procurement_excel.endswith(".xlsx")
    assert Path(procurement_excel).exists()
