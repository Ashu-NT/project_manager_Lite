from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.domain.master_data.party import PartyType
from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog
from src.ui_qml.modules.inventory_procurement.presenters import InventoryPricingWorkspacePresenter
from src.tests.ui_runtime_helpers import login_as


def test_inventory_qml_workspace_catalog_exposes_pricing_workspace(services) -> None:
    services["auth_service"].register_user(
        "inventory-qml-pricing-buyer",
        "StrongPass123",
        role_names=["inventory_manager"],
    )
    services["auth_service"].register_user(
        "inventory-qml-pricing-approver",
        "StrongPass123",
        role_names=["approver"],
    )
    site = services["site_service"].create_site(
        site_code="PRICE-QML",
        name="Pricing Site",
        city="Leipzig",
        currency_code="EUR",
    )
    supplier = services["party_service"].create_party(
        party_code="PRICE-SUP",
        party_name="Pricing Supplier",
        party_type=PartyType.SUPPLIER,
    )
    login_as(services, "inventory-qml-pricing-buyer", "StrongPass123")
    item = services["inventory_item_service"].create_item(
        item_code="PRICE-QML-ITEM",
        name="Pricing Coupling",
        status="ACTIVE",
        stock_uom="EA",
        reorder_point=2,
        reorder_qty=5,
        max_qty=10,
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PRICE-QML-MAIN",
        name="Pricing Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=1,
        uom="EA",
        unit_cost=14.0,
    )
    requisition = services["inventory_procurement_service"].create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Pricing workspace demand",
    )
    requisition_line = services["inventory_procurement_service"].add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=3,
        uom="EA",
        estimated_unit_cost=15.0,
        suggested_supplier_party_id=supplier.id,
    )
    requisition = services["inventory_procurement_service"].submit_requisition(
        requisition.id,
        note="Submit pricing workspace requisition",
    )
    login_as(services, "inventory-qml-pricing-approver", "StrongPass123")
    services["approval_service"].approve_and_apply(
        requisition.approval_request_id,
        note="Approve pricing workspace requisition",
    )
    login_as(services, "inventory-qml-pricing-buyer", "StrongPass123")
    purchase_order = services["inventory_purchasing_service"].create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        source_requisition_id=requisition.id,
    )
    services["inventory_purchasing_service"].add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=3,
        uom="EA",
        unit_price=13.5,
        source_requisition_line_id=requisition_line.id,
    )
    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)

    workspace = catalog.workspace("inventory_procurement.pricing")

    assert workspace["routeId"] == "inventory_procurement.pricing"
    assert workspace["migrationStatus"] == "QML pricing slice active"
    assert catalog.pricingWorkspace.overview["title"] == "Pricing"
    assert catalog.pricingWorkspace.stockSignals["title"] == "Stock Status Signals"
    assert catalog.pricingWorkspace.canExport is True


def test_inventory_qml_pricing_presenter_builds_workspace_state(services) -> None:
    services["auth_service"].register_user(
        "inventory-qml-pricing-pres",
        "StrongPass123",
        role_names=["inventory_manager"],
    )
    services["auth_service"].register_user(
        "inventory-qml-pricing-approver-pres",
        "StrongPass123",
        role_names=["approver"],
    )
    site = services["site_service"].create_site(
        site_code="PRICE-PRES",
        name="Pricing Presenter Site",
        city="Dresden",
        currency_code="EUR",
    )
    supplier = services["party_service"].create_party(
        party_code="PRICE-PRES-SUP",
        party_name="Presenter Pricing Supplier",
        party_type=PartyType.SUPPLIER,
    )
    login_as(services, "inventory-qml-pricing-pres", "StrongPass123")
    item = services["inventory_item_service"].create_item(
        item_code="PRICE-PRES-ITEM",
        name="Presenter Pricing Item",
        status="ACTIVE",
        stock_uom="EA",
        reorder_point=2,
        reorder_qty=4,
        max_qty=8,
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PRICE-PRES-MAIN",
        name="Presenter Pricing Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=1,
        uom="EA",
        unit_cost=9.5,
    )
    requisition = services["inventory_procurement_service"].create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Presenter pricing demand",
    )
    requisition_line = services["inventory_procurement_service"].add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=2,
        uom="EA",
        estimated_unit_cost=11.0,
        suggested_supplier_party_id=supplier.id,
    )
    requisition = services["inventory_procurement_service"].submit_requisition(
        requisition.id,
        note="Submit presenter pricing demand",
    )
    login_as(services, "inventory-qml-pricing-approver-pres", "StrongPass123")
    services["approval_service"].approve_and_apply(
        requisition.approval_request_id,
        note="Approve presenter pricing demand",
    )
    login_as(services, "inventory-qml-pricing-pres", "StrongPass123")
    purchase_order = services["inventory_purchasing_service"].create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        source_requisition_id=requisition.id,
    )
    services["inventory_purchasing_service"].add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=2,
        uom="EA",
        unit_price=10.5,
        source_requisition_line_id=requisition_line.id,
    )
    registry = build_desktop_api_registry(services)
    presenter = InventoryPricingWorkspacePresenter(
        desktop_api=registry.inventory_procurement_pricing
    )

    snapshot = presenter.build_workspace_state(
        site_filter=site.id,
        storeroom_filter=storeroom.id,
        supplier_filter=supplier.id,
        limit_filter="200",
    )

    assert snapshot.overview.title == "Pricing"
    assert snapshot.selected_site_filter == site.id
    assert snapshot.selected_storeroom_filter == storeroom.id
    assert snapshot.selected_supplier_filter == supplier.id
    assert snapshot.stock_rows[0].title.startswith("PRICE-PRES-ITEM")
    assert snapshot.supplier_price_rows[0].status_label.startswith("EUR")
