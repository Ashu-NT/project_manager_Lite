from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryItemCreateCommand,
    InventoryOpeningBalanceCommand,
    InventoryRequisitionCreateCommand,
    InventoryRequisitionLineCreateCommand,
    InventoryReservationCreateCommand,
    InventoryStoreroomCreateCommand,
)
from src.tests.inventory_procurement._inv_procurement_api_helpers import (
    _build_catalog_api,
    _build_dashboard_api,
    _build_inventory_api,
    _build_procurement_api,
    _build_reservations_api,
    _create_shared_inventory_references,
)


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
