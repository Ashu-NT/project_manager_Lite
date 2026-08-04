from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementDashboardDesktopApi,
    InventoryProcurementPricingDesktopApi,
    build_inventory_procurement_catalog_desktop_api,
    build_inventory_procurement_dashboard_desktop_api,
    build_inventory_procurement_inventory_desktop_api,
    build_inventory_procurement_pricing_desktop_api,
    build_inventory_procurement_procurement_desktop_api,
    build_inventory_procurement_reservations_desktop_api,
)
from src.core.platform.domain.master_data.party import PartyType


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
