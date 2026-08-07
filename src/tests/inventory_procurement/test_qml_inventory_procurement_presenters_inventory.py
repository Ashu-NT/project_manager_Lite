from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.domain.master_data.party import PartyType
from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog
from src.ui_qml.modules.inventory_procurement.presenters import InventoryInventoryWorkspacePresenter


def test_inventory_qml_workspace_catalog_exposes_inventory_workspace(services) -> None:
    site = services["site_service"].create_site(
        site_code="INV-QML",
        name="Inventory Site",
        city="Berlin",
        currency_code="EUR",
    )
    manager = services["party_service"].create_party(
        party_code="INV-MGR",
        party_name="Inventory Manager",
        party_type=PartyType.CONTRACTOR,
    )
    item = services["inventory_item_service"].create_item(
        item_code="INV-STK-01",
        name="Inventory Cable",
        status="ACTIVE",
        stock_uom="M",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="INV-MAIN",
        name="Inventory Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
        manager_party_id=manager.id,
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=25,
        uom="M",
        unit_cost=4.5,
    )
    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)

    workspace = catalog.workspace("inventory_procurement.inventory")

    assert workspace["routeId"] == "inventory_procurement.inventory"
    assert workspace["migrationStatus"] == "QML stock operations slice active"
    assert catalog.inventoryWorkspace.overview["title"] == "Inventory"
    assert catalog.inventoryWorkspace.storerooms["items"][0]["title"] == "INV-MAIN - Inventory Main"
    assert catalog.inventoryWorkspace.balances["items"][0]["title"].startswith("INV-STK-01")


def test_inventory_qml_inventory_presenter_builds_workspace_state(services) -> None:
    site = services["site_service"].create_site(
        site_code="INV-PRES",
        name="Inventory Presenter Site",
        city="Hamburg",
        currency_code="EUR",
    )
    manager = services["party_service"].create_party(
        party_code="INV-PRES-MGR",
        party_name="Presenter Manager",
        party_type=PartyType.CONTRACTOR,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="INV-PRES-MAIN",
        name="Presenter Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
        manager_party_id=manager.id,
    )
    item = services["inventory_item_service"].create_item(
        item_code="INV-PRES-ITEM",
        name="Presenter Item",
        status="ACTIVE",
        stock_uom="EA",
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=10,
        uom="EA",
        unit_cost=3.0,
    )
    registry = build_desktop_api_registry(services)
    presenter = InventoryInventoryWorkspacePresenter(
        desktop_api=registry.inventory_procurement_inventory
    )

    snapshot = presenter.build_workspace_state(
        site_filter=site.id,
    )

    assert snapshot.overview.title == "Inventory"
    assert snapshot.storerooms[0].title == "INV-PRES-MAIN - Presenter Main"
    assert snapshot.balances[0].title == "INV-PRES-ITEM - Presenter Item"
    assert snapshot.selected_site_filter == site.id


def test_inventory_qml_inventory_presenter_exposes_foundation_snapshot(services) -> None:
    site = services["site_service"].create_site(
        site_code="INV-FND-PRES",
        name="Inventory Foundation Presenter Site",
        city="Dusseldorf",
        currency_code="EUR",
    )
    supplier = services["party_service"].create_party(
        party_code="INV-FND-SUP",
        party_name="Presenter Foundation Supplier",
        party_type=PartyType.SUPPLIER,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="INV-FND-PRES-MAIN",
        name="Presenter Foundation Main",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )
    item = services["inventory_item_service"].create_item(
        item_code="INV-FND-PRES-ITEM",
        name="Presenter Foundation Item",
        status="ACTIVE",
        stock_uom="EA",
        preferred_party_id=supplier.id,
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=12,
        uom="EA",
        unit_cost=4.5,
    )
    services["inventory_foundation_service"].create_storage_location(
        storeroom_id=storeroom.id,
        location_code="BIN-P1",
        name="Presenter Bin",
        location_type="BIN",
    )
    registry = build_desktop_api_registry(services)
    presenter = InventoryInventoryWorkspacePresenter(
        desktop_api=registry.inventory_procurement_inventory
    )

    snapshot = presenter.build_workspace_state(site_filter=site.id, item_filter=item.id)

    assert snapshot.foundation.title == "Enterprise Inventory Backbone"
    assert snapshot.foundation.locations[0].title == "BIN-P1 - Presenter Bin"
    module_status = {entry.code: entry.is_enabled for entry in snapshot.foundation.module_links}
    assert module_status["project_management"] is True
