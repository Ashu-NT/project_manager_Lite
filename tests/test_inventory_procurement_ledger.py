from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.platform.common.exceptions import ValidationError
from tests.ui_runtime_helpers import login_as


def _create_active_item_and_storeroom(services):
    site = services["site_service"].create_site(
        site_code="LEDGER",
        name="Ledger Site",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code="MOTOR-001",
        name="Motor",
        status="ACTIVE",
        stock_uom="EA",
        reorder_point=4,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="LEDGER-MAIN",
        name="Ledger Main",
        site_id=site.id,
        status="ACTIVE",
    )
    return item, storeroom


def test_inventory_manager_can_post_opening_balance_and_adjustments(services):
    auth = services["auth_service"]
    auth.register_user("inventory-ledger-user", "StrongPass123", role_names=["inventory_manager"])
    item, storeroom = _create_active_item_and_storeroom(services)

    login_as(services, "inventory-ledger-user", "StrongPass123")

    stock_service = services["inventory_stock_service"]
    opened_at = datetime.now(timezone.utc)
    opening = stock_service.post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=10,
        unit_cost=5.0,
        transaction_at=opened_at,
        notes="Initial seed",
    )
    increase = stock_service.post_adjustment(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=2,
        direction="increase",
        unit_cost=7.0,
        transaction_at=opened_at + timedelta(minutes=1),
        notes="Cycle count increase",
    )
    decrease = stock_service.post_adjustment(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=5,
        direction="decrease",
        transaction_at=opened_at + timedelta(minutes=2),
        notes="Scrap adjustment",
    )

    balance = stock_service.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=storeroom.id)
    transactions = stock_service.list_transactions(stock_item_id=item.id, storeroom_id=storeroom.id, limit=10)

    assert opening.transaction_type.value == "OPENING_BALANCE"
    assert increase.resulting_on_hand_qty == pytest.approx(12.0)
    assert decrease.resulting_on_hand_qty == pytest.approx(7.0)
    assert balance is not None
    assert balance.on_hand_qty == pytest.approx(7.0)
    assert balance.available_qty == pytest.approx(7.0)
    assert balance.reorder_required is False
    assert balance.average_cost == pytest.approx((10 * 5.0 + 2 * 7.0) / 12.0)
    assert [row.transaction_type.value for row in transactions] == [
        "ADJUSTMENT_DECREASE",
        "ADJUSTMENT_INCREASE",
        "OPENING_BALANCE",
    ]


def test_inventory_ledger_rejects_invalid_opening_balance_and_negative_stock(services):
    item, storeroom = _create_active_item_and_storeroom(services)
    stock_service = services["inventory_stock_service"]

    stock_service.post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=3,
        unit_cost=2.0,
    )

    with pytest.raises(ValidationError, match="Opening balance has already been posted"):
        stock_service.post_opening_balance(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=1,
        )
    with pytest.raises(ValidationError, match="on-hand quantity negative"):
        stock_service.post_adjustment(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=4,
            direction="decrease",
        )


def test_inventory_ledger_restricts_transactions_to_stock_uom_and_active_masters(services):
    item, storeroom = _create_active_item_and_storeroom(services)
    stock_service = services["inventory_stock_service"]

    with pytest.raises(ValidationError, match="stock UOM"):
        stock_service.post_opening_balance(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            quantity=1,
            uom="BOX",
        )

    inactive_item = services["inventory_item_service"].create_item(
        item_code="MOTOR-002",
        name="Inactive Motor",
        stock_uom="EA",
    )
    with pytest.raises(ValidationError, match="Stock item must be active"):
        stock_service.post_opening_balance(
            stock_item_id=inactive_item.id,
            storeroom_id=storeroom.id,
            quantity=1,
        )

    inactive_storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="LEDGER-DRAFT",
        name="Draft Storeroom",
        site_id=storeroom.site_id,
    )
    with pytest.raises(ValidationError, match="Storeroom must be active"):
        stock_service.post_opening_balance(
            stock_item_id=item.id,
            storeroom_id=inactive_storeroom.id,
            quantity=1,
        )
