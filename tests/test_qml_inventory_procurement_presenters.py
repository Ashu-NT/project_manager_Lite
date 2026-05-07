from src.api.desktop.runtime import build_desktop_api_registry
from src.core.platform.party.domain import PartyType
from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryCatalogWorkspacePresenter,
    InventoryDashboardWorkspacePresenter,
    InventoryInventoryWorkspacePresenter,
)


def test_inventory_qml_workspace_catalog_exposes_dashboard_workspace(services) -> None:
    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)

    workspace = catalog.workspace("inventory_procurement.dashboard")

    assert workspace["routeId"] == "inventory_procurement.dashboard"
    assert workspace["title"] == "Inventory Dashboard"
    assert workspace["migrationStatus"] == "QML dashboard slice active"
    assert catalog.dashboardWorkspace.overview["title"] == "Inventory Dashboard"


def test_inventory_qml_workspace_catalog_exposes_catalog_workspace(services) -> None:
    supplier = services["party_service"].create_party(
        party_code="SUP-QML-01",
        party_name="Catalog Supplier",
        party_type=PartyType.SUPPLIER,
    )
    category = services["inventory_item_category_service"].create_category(
        category_code="SP-QML",
        name="QML Spares",
        category_type="SPARE",
        supports_maintenance_usage=True,
    )
    item = services["inventory_item_service"].create_item(
        item_code="QML-ITEM-01",
        name="QML Gasket",
        status="ACTIVE",
        stock_uom="EA",
        category_code=category.category_code,
        preferred_party_id=supplier.id,
    )
    document = services["document_service"].create_document(
        document_code="QML-DOC-01",
        title="QML Item Manual",
        document_type="MANUAL",
        storage_kind="REFERENCE",
        storage_uri="vault://inventory/qml-item-manual",
    )
    services["inventory_item_service"].link_document(item.id, document_id=document.id)
    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)

    workspace = catalog.workspace("inventory_procurement.catalog")

    assert workspace["routeId"] == "inventory_procurement.catalog"
    assert workspace["migrationStatus"] == "QML CRUD catalog slice active"
    assert catalog.catalogWorkspace.overview["title"] == "Catalog"
    assert catalog.catalogWorkspace.items["items"][0]["title"] == "QML-ITEM-01 - QML Gasket"
    assert catalog.catalogWorkspace.selectedItem["linkedDocuments"][0]["label"].startswith("QML-DOC-01")


def test_inventory_qml_dashboard_presenter_builds_snapshot(services) -> None:
    registry = build_desktop_api_registry(services)
    presenter = InventoryDashboardWorkspacePresenter(
        desktop_api=registry.inventory_procurement_dashboard
    )

    snapshot = presenter.build_workspace_state()

    assert snapshot.overview.title == "Inventory Dashboard"
    assert [section.title for section in snapshot.sections] == [
        "Low Stock Watch",
        "Approval Queue",
        "Receiving Queue",
    ]


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


def test_inventory_qml_catalog_presenter_builds_workspace_state(services) -> None:
    category = services["inventory_item_category_service"].create_category(
        category_code="EQ-QML",
        name="QML Equipment",
        category_type="EQUIPMENT",
        is_equipment=True,
        supports_project_usage=True,
    )
    services["inventory_item_service"].create_item(
        item_code="EQ-QML-01",
        name="QML Pump",
        status="ACTIVE",
        stock_uom="EA",
        category_code=category.category_code,
        is_stocked=True,
    )
    registry = build_desktop_api_registry(services)
    presenter = InventoryCatalogWorkspacePresenter(
        desktop_api=registry.inventory_procurement_catalog
    )

    snapshot = presenter.build_workspace_state(
        usage_filter="equipment",
    )

    assert snapshot.overview.title == "Catalog"
    assert snapshot.categories[0].title == "EQ-QML - QML Equipment"
    assert snapshot.items[0].title == "EQ-QML-01 - QML Pump"
    assert snapshot.selected_usage_filter == "equipment"


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
