from src.api.desktop.runtime import build_desktop_api_registry
from src.core.platform.party.domain import PartyType
from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryCatalogWorkspacePresenter,
    InventoryDashboardWorkspacePresenter,
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
