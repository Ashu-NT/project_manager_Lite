from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.modules.inventory_procurement.domain import (
    CycleCount,
    CycleCountStatus,
    InventoryItemCategory,
    ReorderPolicy,
    StockItem,
    StorageLocation,
    StorageLocationType,
    Storeroom,
)
from src.core.platform.common.exceptions import ValidationError


def test_inventory_catalog_dtos_normalize_fields() -> None:
    category = InventoryItemCategory.create(
        organization_id="  org-1  ",
        category_code="  equip-01  ",
        name="  Generator Sets  ",
        description="  Prime power assets  ",
        category_type=" equipment ",
        is_equipment=False,
        supports_project_usage=True,
        supports_maintenance_usage=True,
    )

    assert category.organization_id == "org-1"
    assert category.category_code == "EQUIP-01"
    assert category.name == "Generator Sets"
    assert category.description == "Prime power assets"
    assert category.category_type == "EQUIPMENT"
    assert category.is_equipment is True

    item = StockItem.create(
        organization_id="  org-1  ",
        item_code="  valve-01  ",
        name="  Control Valve  ",
        description="  Stainless trim  ",
        item_type=" spare ",
        status=" active ",
        stock_uom=" ea ",
        order_uom=" box ",
        issue_uom=" box ",
        order_uom_ratio="12",
        issue_uom_ratio=12.0,
        category_code="  spare-mech  ",
        commodity_code="  mech  ",
        is_stocked=True,
        is_purchase_allowed=True,
        default_reorder_policy="  minmax  ",
        min_qty="2",
        max_qty="12",
        reorder_point="4",
        reorder_qty="6",
        lead_time_days="5",
        shelf_life_days="30",
        preferred_party_id="  supplier-1  ",
        notes="  cool storage  ",
    )

    assert item.organization_id == "org-1"
    assert item.item_code == "VALVE-01"
    assert item.name == "Control Valve"
    assert item.description == "Stainless trim"
    assert item.item_type == "SPARE"
    assert item.status == "ACTIVE"
    assert item.stock_uom == "EA"
    assert item.order_uom == "BOX"
    assert item.issue_uom == "BOX"
    assert item.order_uom_ratio == 12.0
    assert item.issue_uom_ratio == 12.0
    assert item.category_code == "SPARE-MECH"
    assert item.commodity_code == "MECH"
    assert item.default_reorder_policy == "MINMAX"
    assert item.lead_time_days == 5
    assert item.shelf_life_days == 30
    assert item.preferred_party_id == "supplier-1"
    assert item.notes == "cool storage"
    assert item.is_active is True

    storeroom = Storeroom.create(
        organization_id="  org-1  ",
        storeroom_code="  main-01  ",
        name="  Main Warehouse  ",
        site_id="  site-1  ",
        description="  Central issue point  ",
        status=" active ",
        storeroom_type=" main ",
        default_currency_code=" usd ",
        manager_party_id="  manager-1  ",
        notes="  climate controlled  ",
    )

    assert storeroom.organization_id == "org-1"
    assert storeroom.storeroom_code == "MAIN-01"
    assert storeroom.name == "Main Warehouse"
    assert storeroom.description == "Central issue point"
    assert storeroom.status == "ACTIVE"
    assert storeroom.storeroom_type == "MAIN"
    assert storeroom.default_currency_code == "USD"
    assert storeroom.manager_party_id == "manager-1"
    assert storeroom.notes == "climate controlled"
    assert storeroom.is_active is True


def test_inventory_foundation_dtos_normalize_fields_and_validate_ranges() -> None:
    location = StorageLocation.create(
        organization_id="  org-1  ",
        storeroom_id="  store-1  ",
        location_code="  bin-a1  ",
        name="  Bin A1  ",
        parent_location_id="  zone-1  ",
        location_type=" shelf ",
        notes="  Upper rack  ",
    )

    assert location.organization_id == "org-1"
    assert location.storeroom_id == "store-1"
    assert location.location_code == "BIN-A1"
    assert location.name == "Bin A1"
    assert location.parent_location_id == "zone-1"
    assert location.location_type is StorageLocationType.SHELF
    assert location.notes == "Upper rack"

    policy = ReorderPolicy.create(
        organization_id="  org-1  ",
        stock_item_id="  item-1  ",
        storeroom_id="  store-1  ",
        location_id="  loc-1  ",
        policy_name="  Main shelf policy  ",
        min_qty="2",
        max_qty="10",
        reorder_point="4",
        reorder_qty="6",
        economic_order_qty="8",
        lead_time_days="7",
        review_period_days="14",
        preferred_supplier_party_id="  supplier-1  ",
    )

    assert policy.organization_id == "org-1"
    assert policy.stock_item_id == "item-1"
    assert policy.storeroom_id == "store-1"
    assert policy.location_id == "loc-1"
    assert policy.policy_name == "Main shelf policy"
    assert policy.min_qty == 2.0
    assert policy.max_qty == 10.0
    assert policy.reorder_point == 4.0
    assert policy.reorder_qty == 6.0
    assert policy.economic_order_qty == 8.0
    assert policy.lead_time_days == 7
    assert policy.review_period_days == 14
    assert policy.preferred_supplier_party_id == "supplier-1"

    cycle_count = CycleCount(
        id="cycle-1",
        organization_id="  org-1  ",
        cycle_count_number="  cc-001  ",
        stock_item_id="  item-1  ",
        storeroom_id="  store-1  ",
        location_id="  loc-1  ",
        scheduled_count_date="2026-07-01",
        status=" completed ",
        expected_qty="10",
        counted_qty="12.5",
        variance_qty="-99",
        counted_by_user_id="  user-1  ",
        counted_by_username="  Alex Counter  ",
        created_at=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        notes="  counted and verified  ",
    )

    assert cycle_count.organization_id == "org-1"
    assert cycle_count.cycle_count_number == "CC-001"
    assert cycle_count.location_id == "loc-1"
    assert cycle_count.scheduled_count_date == date(2026, 7, 1)
    assert cycle_count.status is CycleCountStatus.COMPLETED
    assert cycle_count.expected_qty == 10.0
    assert cycle_count.counted_qty == 12.5
    assert cycle_count.variance_qty == 2.5
    assert cycle_count.counted_by_user_id == "user-1"
    assert cycle_count.counted_by_username == "Alex Counter"
    assert cycle_count.notes == "counted and verified"


def test_inventory_catalog_and_foundation_dtos_raise_expected_validation_codes() -> None:
    with pytest.raises(ValidationError) as exc_uom:
        StockItem.create(
            organization_id="org-1",
            item_code="VALVE-ALT",
            name="Alternate Valve",
            stock_uom="EA",
            order_uom="BOX",
        )
    assert exc_uom.value.code == "INVENTORY_UOM_FACTOR_REQUIRED"

    with pytest.raises(ValidationError) as exc_policy:
        ReorderPolicy.create(
            organization_id="org-1",
            stock_item_id="item-1",
            storeroom_id="store-1",
            min_qty=6,
            max_qty=3,
        )
    assert exc_policy.value.code == "INVENTORY_REORDER_POLICY_MAX_INVALID"

    created_at = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError) as exc_cycle:
        CycleCount(
            id="cycle-1",
            organization_id="org-1",
            cycle_count_number="CC-002",
            stock_item_id="item-1",
            storeroom_id="store-1",
            status="COMPLETED",
            expected_qty=10,
            counted_qty=8,
            created_at=created_at,
            completed_at=created_at - timedelta(minutes=30),
        )
    assert exc_cycle.value.code == "INVENTORY_CYCLE_COUNT_COMPLETED_RANGE_INVALID"
