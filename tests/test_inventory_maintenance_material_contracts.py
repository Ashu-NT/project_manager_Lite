from __future__ import annotations

from uuid import uuid4

import pytest

from core.modules.inventory_procurement.domain import StockTransactionType
from core.modules.inventory_procurement.services.maintenance_integration import (
    MaintenanceMaterialAvailabilityStatus,
)
from core.platform.common.exceptions import ValidationError
from core.platform.notifications.domain_events import domain_events
from core.platform.party.domain import PartyType


def _suffix() -> str:
    return uuid4().hex[:6].upper()


def _enable_inventory_module(services) -> None:
    services["module_catalog_service"].set_module_state(
        "inventory_procurement",
        licensed=True,
        enabled=True,
    )


def _create_material_context(
    services,
    *,
    category_type: str = "SPARE",
    maintenance_enabled: bool = True,
    is_stocked: bool = True,
    is_purchase_allowed: bool = True,
):
    suffix = _suffix()
    site = services["site_service"].create_site(
        site_code=f"MM-{suffix}",
        name=f"Maintenance Site {suffix}",
        currency_code="EUR",
    )
    supplier = services["party_service"].create_party(
        party_code=f"SUP-{suffix}",
        party_name=f"Maintenance Supplier {suffix}",
        party_type=PartyType.SUPPLIER,
    )
    category = services["inventory_item_category_service"].create_category(
        category_code=f"CAT-{suffix}",
        name=f"Maintenance Category {suffix}",
        category_type=category_type,
        supports_maintenance_usage=maintenance_enabled,
        is_equipment=category_type == "EQUIPMENT",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"STR-{suffix}",
        name=f"Maintenance Storeroom {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"ITEM-{suffix}",
        name=f"Maintenance Item {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        category_code=category.category_code,
        preferred_party_id=supplier.id,
        is_stocked=is_stocked,
        is_purchase_allowed=is_purchase_allowed,
    )
    return site, supplier, category, storeroom, item


def test_maintenance_material_service_reports_stock_availability_statuses(services):
    _enable_inventory_module(services)
    _, _, _, storeroom, item = _create_material_context(services)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=10,
        unit_cost=4.5,
    )

    maintenance_materials = services["inventory_maintenance_material_service"]

    available = maintenance_materials.get_material_availability(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=4,
        source_reference_type="maintenance_work_order",
        source_reference_id="MWO-100",
    )
    partial = maintenance_materials.get_material_availability(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=12,
        source_reference_type="maintenance_work_order",
        source_reference_id="MWO-101",
    )

    assert available.status == MaintenanceMaterialAvailabilityStatus.AVAILABLE_FROM_STOCK
    assert available.can_reserve is True
    assert available.can_issue_from_stock is True
    assert available.can_direct_procure is False
    assert available.available_stock_qty == 10
    assert available.missing_stock_qty == 0

    assert partial.status == MaintenanceMaterialAvailabilityStatus.PARTIALLY_AVAILABLE_FROM_STOCK
    assert partial.can_reserve is False
    assert partial.can_issue_from_stock is True
    assert partial.can_direct_procure is True
    assert partial.available_stock_qty == 10
    assert partial.missing_stock_qty == 2


def test_maintenance_material_service_reserves_issues_and_returns_stock(services):
    _enable_inventory_module(services)
    _, _, _, storeroom, item = _create_material_context(services)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=10,
        unit_cost=6.0,
    )
    maintenance_materials = services["inventory_maintenance_material_service"]
    seen: list[str] = []

    def _handler(reference_key: str) -> None:
        seen.append(reference_key)

    domain_events.inventory_maintenance_materials_changed.connect(_handler)
    try:
        reserved = maintenance_materials.reserve_material(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=4,
            source_reference_type="maintenance_work_order",
            source_reference_id="MWO-200",
            notes="Reserve for planned shutdown",
        )
        issued = maintenance_materials.issue_reserved_material(
            reservation_id=reserved.reservation.id,
            quantity=2,
            note="Issue first batch",
        )
        returned = maintenance_materials.return_material(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=1,
            source_reference_type="maintenance_work_order",
            source_reference_id="MWO-200",
            notes="Return unused part",
        )
    finally:
        domain_events.inventory_maintenance_materials_changed.disconnect(_handler)

    reservations = maintenance_materials.list_reservations_for_source(
        source_reference_type="maintenance_work_order",
        source_reference_id="MWO-200",
        include_closed=False,
    )

    assert reserved.reservation is not None
    assert issued.reservation is not None
    assert returned.transaction is not None
    assert issued.reservation.status.value == "PARTIALLY_ISSUED"
    assert issued.reservation.remaining_qty == 2
    assert returned.transaction.transaction_type == StockTransactionType.RETURN
    assert returned.transaction.reference_type == "maintenance_work_order"
    assert returned.transaction.reference_id == "MWO-200"
    assert [row.id for row in reservations] == [reserved.reservation.id]
    assert maintenance_materials.list_reservations_for_source(
        source_reference_type="maintenance_work_order",
        source_reference_id="MWO-OTHER",
    ) == []
    assert seen == [
        "maintenance_work_order:MWO-200",
        "maintenance_work_order:MWO-200",
        "maintenance_work_order:MWO-200",
    ]


def test_maintenance_material_service_escalates_shortage_to_procurement(services):
    _enable_inventory_module(services)
    _, _, _, storeroom, item = _create_material_context(
        services,
        is_stocked=False,
        is_purchase_allowed=True,
    )
    maintenance_materials = services["inventory_maintenance_material_service"]

    availability = maintenance_materials.get_material_availability(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=5,
        source_reference_type="maintenance_work_order",
        source_reference_id="MWO-300",
    )
    escalation = maintenance_materials.escalate_shortage_to_requisition(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=5,
        source_reference_type="maintenance_work_order",
        source_reference_id="MWO-300",
        notes="Direct-charge seal kit",
    )

    requisitions = maintenance_materials.list_requisitions_for_source(
        source_reference_type="maintenance_work_order",
        source_reference_id="MWO-300",
    )

    assert availability.status == MaintenanceMaterialAvailabilityStatus.DIRECT_PROCUREMENT_ONLY
    assert escalation.availability.status == MaintenanceMaterialAvailabilityStatus.DIRECT_PROCUREMENT_ONLY
    assert escalation.requisition.source_reference_type == "maintenance_work_order"
    assert escalation.requisition.source_reference_id == "MWO-300"
    assert escalation.requisition_line.quantity_requested == 5
    assert escalation.requisition_line.stock_item_id == item.id
    assert [row.id for row in requisitions] == [escalation.requisition.id]


def test_maintenance_material_service_rejects_items_not_enabled_for_maintenance_usage(services):
    _enable_inventory_module(services)
    _, _, _, storeroom, item = _create_material_context(
        services,
        maintenance_enabled=False,
    )
    maintenance_materials = services["inventory_maintenance_material_service"]

    availability = maintenance_materials.get_material_availability(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=2,
        source_reference_type="maintenance_work_order",
        source_reference_id="MWO-400",
    )

    assert availability.status == MaintenanceMaterialAvailabilityStatus.NOT_MAINTENANCE_ENABLED

    with pytest.raises(ValidationError, match="not enabled for maintenance usage"):
        maintenance_materials.reserve_material(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=2,
            source_reference_type="maintenance_work_order",
            source_reference_id="MWO-400",
        )
    with pytest.raises(ValidationError, match="not enabled for maintenance usage"):
        maintenance_materials.escalate_shortage_to_requisition(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=2,
            source_reference_type="maintenance_work_order",
            source_reference_id="MWO-400",
        )
