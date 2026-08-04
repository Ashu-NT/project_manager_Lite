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
        module_runtime_service=services["module_runtime_service"],
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


def test_inventory_inventory_desktop_api_builds_enterprise_foundation_snapshot(services) -> None:
    site, supplier, _ = _create_shared_inventory_references(services)
    catalog_api = _build_catalog_api(services)
    inventory_api = _build_inventory_api(services)
    auth = services["auth_service"]
    auth.register_user("inventory-foundation-api-user", "StrongPass123", role_names=["inventory_manager"])
    login_as(services, "inventory-foundation-api-user", "StrongPass123")

    item = catalog_api.create_item(
        InventoryItemCreateCommand(
            item_code="FOUND-API-ITEM",
            name="Foundation API Item",
            status="ACTIVE",
            stock_uom="EA",
            preferred_party_id=supplier.id,
        )
    )
    storeroom = inventory_api.create_storeroom(
        InventoryStoreroomCreateCommand(
            storeroom_code="FOUND-API-MAIN",
            name="Foundation API Main",
            site_id=site.id,
            status="ACTIVE",
            storeroom_type="MAIN",
        )
    )
    inventory_api.post_opening_balance(
        InventoryOpeningBalanceCommand(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=15,
            uom="EA",
            unit_cost=10.0,
        )
    )
    location = inventory_api.create_storage_location(
        InventoryLocationCreateCommand(
            storeroom_id=storeroom.id,
            location_code="BIN-F1",
            name="Foundation Bin",
            location_type="BIN",
        )
    )
    policy = inventory_api.upsert_reorder_policy(
        InventoryReorderPolicyUpsertCommand(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            location_id=location.id,
            policy_name="Bin replenishment",
            min_qty=2,
            max_qty=10,
            reorder_point=4,
            reorder_qty=5,
            preferred_supplier_party_id=supplier.id,
        )
    )
    cycle_count = inventory_api.schedule_cycle_count(
        InventoryCycleCountCreateCommand(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            location_id=location.id,
            scheduled_count_date="2026-06-05",
        )
    )

    snapshot = inventory_api.build_foundation_snapshot(
        site_id=site.id,
        storeroom_id=storeroom.id,
        stock_item_id=item.id,
    )

    assert snapshot.title == "Enterprise Inventory Backbone"
    assert snapshot.locations[0].location_code == "BIN-F1"
    assert snapshot.reorder_policies[0].id == policy.id
    assert snapshot.cycle_counts[0].id == cycle_count.id
    module_status = {entry.code: entry.is_enabled for entry in snapshot.module_links}
    assert module_status["project_management"] is True
    assert module_status["maintenance_management"] is False
