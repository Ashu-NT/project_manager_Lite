from __future__ import annotations

from uuid import uuid4

import pytest

from core.platform.common.exceptions import ValidationError
from tests.ui_runtime_helpers import login_as


def _create_reservation_context(services):
    suffix = uuid4().hex[:6].upper()
    site = services["site_service"].create_site(
        site_code=f"RES-{suffix}",
        name=f"Reservation Site {suffix}",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"BOLT-{suffix}",
        name=f"Bolt {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"RES-MAIN-{suffix}",
        name=f"Reservation Main {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    return site, storeroom, item


def test_create_reservation_reduces_available_qty_without_changing_on_hand(services):
    auth = services["auth_service"]
    auth.register_user("inventory-reserver", "StrongPass123", role_names=["inventory_manager"])
    _site, storeroom, item = _create_reservation_context(services)

    login_as(services, "inventory-reserver", "StrongPass123")

    stock = services["inventory_stock_service"]
    reservations = services["inventory_reservation_service"]

    stock.post_opening_balance(stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=2.5)
    reservation = reservations.create_reservation(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        reserved_qty=4,
        source_reference_type="work_order",
        source_reference_id="WO-100",
        notes="Reserve for planned work",
    )
    balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=storeroom.id)
    transactions = stock.list_transactions(stock_item_id=item.id, storeroom_id=storeroom.id)

    assert reservation.status.value == "ACTIVE"
    assert reservation.remaining_qty == pytest.approx(4.0)
    assert balance is not None
    assert balance.on_hand_qty == pytest.approx(10.0)
    assert balance.reserved_qty == pytest.approx(4.0)
    assert balance.available_qty == pytest.approx(6.0)
    assert transactions[0].transaction_type.value == "RESERVATION_HOLD"


def test_release_reservation_restores_available_qty(services):
    auth = services["auth_service"]
    auth.register_user("inventory-release", "StrongPass123", role_names=["inventory_manager"])
    _site, storeroom, item = _create_reservation_context(services)

    login_as(services, "inventory-release", "StrongPass123")

    stock = services["inventory_stock_service"]
    reservations = services["inventory_reservation_service"]

    stock.post_opening_balance(stock_item_id=item.id, storeroom_id=storeroom.id, quantity=8, unit_cost=1.0)
    reservation = reservations.create_reservation(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        reserved_qty=3,
        source_reference_type="task",
        source_reference_id="TASK-55",
    )
    released = reservations.release_reservation(reservation.id, note="Demand removed")
    balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=storeroom.id)
    transactions = stock.list_transactions(stock_item_id=item.id, storeroom_id=storeroom.id)

    assert released.status.value == "RELEASED"
    assert released.remaining_qty == pytest.approx(0.0)
    assert released.released_at is not None
    assert balance.reserved_qty == pytest.approx(0.0)
    assert balance.available_qty == pytest.approx(8.0)
    assert [tx.transaction_type.value for tx in transactions[:2]] == ["RESERVATION_RELEASE", "RESERVATION_HOLD"]


def test_reservations_validate_source_reference_and_available_qty(services):
    auth = services["auth_service"]
    auth.register_user("inventory-reservation-rules", "StrongPass123", role_names=["inventory_manager"])
    _site, storeroom, item = _create_reservation_context(services)

    login_as(services, "inventory-reservation-rules", "StrongPass123")

    stock = services["inventory_stock_service"]
    reservations = services["inventory_reservation_service"]

    stock.post_opening_balance(stock_item_id=item.id, storeroom_id=storeroom.id, quantity=2)

    with pytest.raises(ValidationError, match="source reference type and ID"):
        reservations.create_reservation(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            reserved_qty=1,
            source_reference_type="",
            source_reference_id="",
        )

    with pytest.raises(ValidationError, match="available quantity negative"):
        reservations.create_reservation(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            reserved_qty=3,
            source_reference_type="work_order",
            source_reference_id="WO-200",
        )
