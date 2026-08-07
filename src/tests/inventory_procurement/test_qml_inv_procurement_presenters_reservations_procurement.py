from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.domain.master_data.party import PartyType
from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryProcurementProcurementWorkspacePresenter,
    InventoryReservationsWorkspacePresenter,
)
from src.tests.ui_runtime_helpers import login_as


def test_inventory_qml_workspace_catalog_exposes_reservations_workspace(services) -> None:
    site = services["site_service"].create_site(
        site_code="RES-QML",
        name="Reservations Site",
        city="Munich",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code="RES-QML-ITEM",
        name="Reservations Bolt",
        status="ACTIVE",
        stock_uom="EA",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="RES-QML-MAIN",
        name="Reservations Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=18,
        uom="EA",
        unit_cost=2.0,
    )
    services["inventory_reservation_service"].create_reservation(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        reserved_qty=4,
        uom="EA",
        source_reference_type="task",
        source_reference_id="RES-QML-TASK-1",
        notes="Hold for QML reservation workspace.",
    )
    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)

    workspace = catalog.workspace("inventory_procurement.reservations")

    assert workspace["routeId"] == "inventory_procurement.reservations"
    assert workspace["migrationStatus"] == "QML reservations slice active"
    assert catalog.reservationsWorkspace.overview["title"] == "Reservations"
    assert (
        catalog.reservationsWorkspace.reservations["items"][0]["title"].startswith(
            "INV-RES-"
        )
    )


def test_inventory_qml_reservations_presenter_builds_workspace_state(services) -> None:
    site = services["site_service"].create_site(
        site_code="RES-PRES",
        name="Reservations Presenter Site",
        city="Frankfurt",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code="RES-PRES-ITEM",
        name="Presenter Reservation Item",
        status="ACTIVE",
        stock_uom="EA",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="RES-PRES-MAIN",
        name="Presenter Reservations Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=30,
        uom="EA",
        unit_cost=1.75,
    )
    services["inventory_reservation_service"].create_reservation(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        reserved_qty=6,
        uom="EA",
        source_reference_type="work_order",
        source_reference_id="WO-QML-77",
        notes="Presenter reservation.",
    )
    registry = build_desktop_api_registry(services)
    presenter = InventoryReservationsWorkspacePresenter(
        desktop_api=registry.inventory_procurement_reservations
    )

    snapshot = presenter.build_workspace_state(
        storeroom_filter=storeroom.id,
    )

    assert snapshot.overview.title == "Reservations"
    assert snapshot.selected_storeroom_filter == storeroom.id
    assert snapshot.reservations[0].title.startswith("INV-RES-")
    assert snapshot.selected_reservation_detail.fields[0].label == "Item"


def test_inventory_qml_workspace_catalog_exposes_procurement_workspace(services) -> None:
    services["auth_service"].register_user(
        "inventory-qml-buyer",
        "StrongPass123",
        role_names=["inventory_manager"],
    )
    site = services["site_service"].create_site(
        site_code="PROC-QML",
        name="Procurement Site",
        city="Stuttgart",
        currency_code="EUR",
    )
    supplier = services["party_service"].create_party(
        party_code="PROC-SUP",
        party_name="Procurement Supplier",
        party_type=PartyType.SUPPLIER,
    )
    login_as(services, "inventory-qml-buyer", "StrongPass123")
    item = services["inventory_item_service"].create_item(
        item_code="PROC-QML-ITEM",
        name="Procurement Valve",
        status="ACTIVE",
        stock_uom="EA",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PROC-QML-MAIN",
        name="Procurement Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    requisition = services["inventory_procurement_service"].create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="QML procurement demand",
        priority="HIGH",
    )
    services["inventory_procurement_service"].add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=8,
        uom="EA",
        estimated_unit_cost=12.5,
        suggested_supplier_party_id=supplier.id,
    )
    purchase_order = services["inventory_purchasing_service"].create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
    )
    services["inventory_purchasing_service"].add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=8,
        uom="EA",
        unit_price=12.5,
    )
    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)

    workspace = catalog.workspace("inventory_procurement.procurement")

    assert workspace["routeId"] == "inventory_procurement.procurement"
    assert workspace["migrationStatus"] == "QML procurement slice active"
    assert catalog.procurementWorkspace.overview["title"] == "Procurement"
    assert catalog.procurementWorkspace.purchaseOrders["items"][0]["title"].startswith(
        "PO-"
    ) or catalog.procurementWorkspace.purchaseOrders["items"][0]["title"]


def test_inventory_qml_procurement_presenter_builds_workspace_state(services) -> None:
    services["auth_service"].register_user(
        "inventory-qml-proc-buyer",
        "StrongPass123",
        role_names=["inventory_manager"],
    )
    site = services["site_service"].create_site(
        site_code="PROC-PRES",
        name="Procurement Presenter Site",
        city="Cologne",
        currency_code="EUR",
    )
    supplier = services["party_service"].create_party(
        party_code="PROC-PRES-SUP",
        party_name="Presenter Supplier",
        party_type=PartyType.SUPPLIER,
    )
    login_as(services, "inventory-qml-proc-buyer", "StrongPass123")
    item = services["inventory_item_service"].create_item(
        item_code="PROC-PRES-ITEM",
        name="Presenter Gasket",
        status="ACTIVE",
        stock_uom="EA",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PROC-PRES-MAIN",
        name="Presenter Procurement Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    requisition = services["inventory_procurement_service"].create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Presenter procurement demand",
        priority="NORMAL",
    )
    services["inventory_procurement_service"].add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        uom="EA",
        estimated_unit_cost=4.0,
        suggested_supplier_party_id=supplier.id,
    )
    purchase_order = services["inventory_purchasing_service"].create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
    )
    services["inventory_purchasing_service"].add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=5,
        uom="EA",
        unit_price=4.0,
    )
    registry = build_desktop_api_registry(services)
    presenter = InventoryProcurementProcurementWorkspacePresenter(
        desktop_api=registry.inventory_procurement_procurement
    )

    snapshot = presenter.build_workspace_state(
        site_filter=site.id,
        selected_requisition_id=requisition.id,
        selected_purchase_order_id=purchase_order.id,
    )

    assert snapshot.overview.title == "Procurement"
    assert snapshot.selected_site_filter == site.id
    assert snapshot.requisitions[0].title.startswith("PR-") or snapshot.requisitions[0].title
    assert snapshot.requisitions[0].state["requestingSiteLabel"] == f"{site.site_code} - {site.name}"
    assert (
        snapshot.requisitions[0].state["requestingStoreroomLabel"]
        == f"{storeroom.storeroom_code} - {storeroom.name}"
    )
    assert snapshot.purchase_orders[0].title
    assert snapshot.purchase_orders[0].state["siteLabel"] == f"{site.site_code} - {site.name}"
    assert (
        snapshot.purchase_orders[0].state["supplierLabel"]
        == f"{supplier.party_code} - {supplier.party_name}"
    )
    assert snapshot.selected_purchase_order_detail.fields[0].label == "Site"
