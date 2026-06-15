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
from src.core.platform.party.domain import PartyType
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
