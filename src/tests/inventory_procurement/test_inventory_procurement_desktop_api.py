from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from src.api.desktop.runtime import build_desktop_api_registry
from src.core.modules.inventory_procurement.api.desktop import (
    InventoryAdjustmentCommand,
    InventoryCategoryCreateCommand,
    InventoryIssueCommand,
    InventoryItemCreateCommand,
    InventoryItemUpdateCommand,
    InventoryOpeningBalanceCommand,
    InventoryProcurementDashboardDesktopApi,
    InventoryProcurementPricingDesktopApi,
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
from src.core.platform.party.domain import PartyType
from tests.ui_runtime_helpers import login_as


EXPECTED_INVENTORY_WORKSPACE_KEYS = [
    "dashboard",
    "catalog",
    "inventory",
    "reservations",
    "procurement",
    "pricing",
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


def test_inventory_procurement_desktop_api_lists_workspace_descriptors() -> None:
    api = build_inventory_procurement_workspace_desktop_api()

    descriptors = api.list_workspaces()

    assert [descriptor.key for descriptor in descriptors] == EXPECTED_INVENTORY_WORKSPACE_KEYS
    assert descriptors[0].title == "Dashboard"
    assert api.get_workspace("inventory_procurement.procurement").title == "Procurement"
    assert api.get_workspace("inventory_procurement.unknown") is None


def test_inventory_catalog_desktop_api_mutates_categories_items_and_document_links(services) -> None:
    _, supplier, _ = _create_shared_inventory_references(services)
    document = services["document_service"].create_document(
        document_code="INV-DOC-001",
        title="Bearing Manual",
        document_type="MANUAL",
        storage_kind="REFERENCE",
        storage_uri="vault://inventory/bearing-manual",
    )
    api = _build_catalog_api(services)

    category = api.create_category(
        InventoryCategoryCreateCommand(
            category_code="SP-BRG",
            name="Bearings",
            category_type="SPARE",
            supports_maintenance_usage=True,
        )
    )
    item = api.create_item(
        InventoryItemCreateCommand(
            item_code="BRG-100",
            name="Bearing 100",
            status="ACTIVE",
            stock_uom="EA",
            category_code=category.category_code,
            preferred_party_id=supplier.id,
            reorder_point=4,
            reorder_qty=10,
            max_qty=20,
        )
    )
    updated = api.update_item(
        InventoryItemUpdateCommand(
            item_id=item.id,
            item_code=item.item_code,
            name="Bearing 100 Rev A",
            status="ACTIVE",
            stock_uom="EA",
            category_code=category.category_code,
            preferred_party_id=supplier.id,
            reorder_point=6,
            reorder_qty=12,
            max_qty=24,
            expected_version=item.version,
        )
    )

    linked_documents = api.link_document(item.id, document_id=document.id, link_role="manual")
    items = api.list_items(active_only=None)

    assert category.category_type == "SPARE"
    assert item.preferred_party_label.startswith("SUP-INV - ")
    assert updated.name == "Bearing 100 Rev A"
    assert updated.reorder_point == 6.0
    assert linked_documents[0].label == "INV-DOC-001 - Bearing Manual"
    assert [row.item_code for row in items] == ["BRG-100"]

    api.unlink_document(item.id, document_id=document.id, link_role="manual")

    assert api.list_linked_documents(item.id, active_only=True) == ()


def test_inventory_inventory_desktop_api_mutates_storerooms_and_stock_flows(services) -> None:
    site, _, manager = _create_shared_inventory_references(services)
    catalog_api = _build_catalog_api(services)
    inventory_api = _build_inventory_api(services)

    item = catalog_api.create_item(
        InventoryItemCreateCommand(
            item_code="CABLE-001",
            name="Control Cable",
            status="ACTIVE",
            stock_uom="M",
        )
    )
    source = inventory_api.create_storeroom(
        InventoryStoreroomCreateCommand(
            storeroom_code="MAIN",
            name="Main Storeroom",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
            manager_party_id=manager.id,
        )
    )
    destination = inventory_api.create_storeroom(
        InventoryStoreroomCreateCommand(
            storeroom_code="AUX",
            name="Aux Storeroom",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="AUX",
        )
    )

    opening = inventory_api.post_opening_balance(
        InventoryOpeningBalanceCommand(
            stock_item_id=item.id,
            storeroom_id=source.id,
            quantity=100,
            uom="M",
            unit_cost=2.5,
        )
    )
    adjustment = inventory_api.post_adjustment(
        InventoryAdjustmentCommand(
            stock_item_id=item.id,
            storeroom_id=source.id,
            quantity=10,
            direction="INCREASE",
            uom="M",
        )
    )
    outbound, inbound = inventory_api.transfer_stock(
        InventoryTransferCommand(
            stock_item_id=item.id,
            source_storeroom_id=source.id,
            destination_storeroom_id=destination.id,
            quantity=25,
            uom="M",
        )
    )
    issued = inventory_api.issue_stock(
        InventoryIssueCommand(
            stock_item_id=item.id,
            storeroom_id=destination.id,
            quantity=5,
            uom="M",
        )
    )
    balances = inventory_api.list_balances()

    assert opening.transaction_type == "OPENING_BALANCE"
    assert adjustment.transaction_type == "ADJUSTMENT_INCREASE"
    assert outbound.transaction_type == "TRANSFER_OUT"
    assert inbound.transaction_type == "TRANSFER_IN"
    assert issued.transaction_type == "ISSUE"
    assert len(balances) == 2
    assert {row.storeroom_label for row in balances} == {
        "AUX - Aux Storeroom",
        "MAIN - Main Storeroom",
    }


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


def test_inventory_dashboard_desktop_api_builds_service_snapshot(services) -> None:
    site, supplier, _ = _create_shared_inventory_references(services)
    catalog_api = _build_catalog_api(services)
    inventory_api = _build_inventory_api(services)
    reservations_api = _build_reservations_api(services)
    procurement_api = _build_procurement_api(services)
    dashboard_api = _build_dashboard_api(services)

    item = catalog_api.create_item(
        InventoryItemCreateCommand(
            item_code="FLT-001",
            name="Filter Cartridge",
            status="ACTIVE",
            stock_uom="EA",
            reorder_point=5,
            reorder_qty=10,
            max_qty=20,
        )
    )
    storeroom = inventory_api.create_storeroom(
        InventoryStoreroomCreateCommand(
            storeroom_code="DASH-MAIN",
            name="Dashboard Main",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
        )
    )
    inventory_api.post_opening_balance(
        InventoryOpeningBalanceCommand(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=3,
            uom="EA",
        )
    )
    reservations_api.create_reservation(
        InventoryReservationCreateCommand(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            reserved_qty=1,
            uom="EA",
            source_reference_type="task",
            source_reference_id="dash-task-1",
        )
    )
    requisition = procurement_api.create_requisition(
        InventoryRequisitionCreateCommand(
            requesting_site_id=site.id,
            requesting_storeroom_id=storeroom.id,
            purpose="Top up filters",
        )
    )
    procurement_api.add_requisition_line(
        InventoryRequisitionLineCreateCommand(
            requisition_id=requisition.id,
            stock_item_id=item.id,
            quantity_requested=10,
            uom="EA",
            estimated_unit_cost=15.0,
            suggested_supplier_party_id=supplier.id,
        )
    )
    procurement_api.submit_requisition(requisition.id, note="Queue dashboard approval")

    snapshot = dashboard_api.build_snapshot()

    metric_by_label = {metric.label: metric for metric in snapshot.metrics}

    assert snapshot.title == "Inventory Dashboard"
    assert metric_by_label["Items"].value == "1"
    assert metric_by_label["Storerooms"].value == "1"
    assert metric_by_label["Open Reservations"].value == "1"
    assert metric_by_label["Awaiting Approval"].value == "1"
    assert [section.title for section in snapshot.sections] == [
        "Low Stock Watch",
        "Approval Queue",
        "Receiving Queue",
    ]


def test_inventory_pricing_desktop_api_builds_snapshot_and_exports_reports(
    services,
    tmp_path,
) -> None:
    services["module_catalog_service"].set_module_state(
        "inventory_procurement",
        licensed=True,
        enabled=True,
    )
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


def test_build_desktop_api_registry_exposes_inventory_adapters(services) -> None:
    registry = build_desktop_api_registry(services)

    assert registry.inventory_procurement_workspaces.list_workspaces()[0].key == "dashboard"
    assert registry.inventory_procurement_catalog.list_item_statuses()[0].value == "DRAFT"
    assert registry.inventory_procurement_inventory.list_transaction_types()[0].value == "OPENING_BALANCE"
    assert registry.inventory_procurement_reservations.list_statuses()[0].value == "ACTIVE"
    assert registry.inventory_procurement_procurement.list_requisition_statuses()[0].value == "DRAFT"
    assert registry.inventory_procurement_dashboard.build_empty_snapshot().title == "Inventory Dashboard"
    assert registry.inventory_procurement_pricing.build_empty_snapshot().title == "Pricing"


def test_inventory_procurement_desktop_api_does_not_import_qml_or_legacy_ui() -> None:
    root = Path("src/core/modules/inventory_procurement/api/desktop")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))

    assert "src.ui_qml" not in combined
    assert "ui.modules.inventory_procurement" not in combined
    assert "src.ui." not in combined
