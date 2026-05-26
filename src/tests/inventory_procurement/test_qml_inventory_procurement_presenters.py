from src.api.desktop.runtime import build_desktop_api_registry
from src.core.platform.party.domain import PartyType
from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryCatalogWorkspacePresenter,
    InventoryDashboardWorkspacePresenter,
    InventoryInventoryWorkspacePresenter,
    InventoryPricingWorkspacePresenter,
    InventoryProcurementProcurementWorkspacePresenter,
    InventoryReservationsWorkspacePresenter,
)
from tests.ui_runtime_helpers import login_as


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
    assert snapshot.purchase_orders[0].title
    assert snapshot.selected_purchase_order_detail.fields[0].label == "Site"


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
