from __future__ import annotations

from uuid import uuid4

import pytest

from core.platform.common.exceptions import ValidationError
from tests.ui_runtime_helpers import login_as


def _create_movement_context(services):
    suffix = uuid4().hex[:6].upper()
    site = services["site_service"].create_site(
        site_code=f"MOV-{suffix}",
        name=f"Movement Site {suffix}",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"VALVE-{suffix}",
        name=f"Valve {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    source = services["inventory_service"].create_storeroom(
        storeroom_code=f"MOV-SRC-{suffix}",
        name=f"Movement Source {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    destination = services["inventory_service"].create_storeroom(
        storeroom_code=f"MOV-DST-{suffix}",
        name=f"Movement Destination {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    return site, item, source, destination


def test_issue_and_return_update_stock_positions(services):
    auth = services["auth_service"]
    auth.register_user("inventory-mover", "StrongPass123", role_names=["inventory_manager"])
    _site, item, source, _destination = _create_movement_context(services)

    login_as(services, "inventory-mover", "StrongPass123")

    stock = services["inventory_stock_service"]
    stock.post_opening_balance(stock_item_id=item.id, storeroom_id=source.id, quantity=10, unit_cost=3.0)

    issued = stock.issue_stock(
        stock_item_id=item.id,
        storeroom_id=source.id,
        quantity=3,
        reference_type="task_issue",
        reference_id="TASK-10",
    )
    returned = stock.return_stock(
        stock_item_id=item.id,
        storeroom_id=source.id,
        quantity=2,
        reference_type="task_return",
        reference_id="TASK-10",
    )
    balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=source.id)

    assert issued.transaction_type.value == "ISSUE"
    assert returned.transaction_type.value == "RETURN"
    assert balance is not None
    assert balance.on_hand_qty == pytest.approx(9.0)
    assert balance.available_qty == pytest.approx(9.0)


def test_transfer_creates_destination_balance_and_pair_transactions(services):
    auth = services["auth_service"]
    auth.register_user("inventory-transfer", "StrongPass123", role_names=["inventory_manager"])
    _site, item, source, destination = _create_movement_context(services)

    login_as(services, "inventory-transfer", "StrongPass123")

    stock = services["inventory_stock_service"]
    stock.post_opening_balance(stock_item_id=item.id, storeroom_id=source.id, quantity=5, unit_cost=7.5)

    outbound, inbound = stock.transfer_stock(
        stock_item_id=item.id,
        source_storeroom_id=source.id,
        destination_storeroom_id=destination.id,
        quantity=2,
        notes="Move to satellite store",
    )
    source_balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=source.id)
    destination_balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=destination.id)

    assert outbound.transaction_type.value == "TRANSFER_OUT"
    assert inbound.transaction_type.value == "TRANSFER_IN"
    assert outbound.reference_id == inbound.reference_id
    assert source_balance.on_hand_qty == pytest.approx(3.0)
    assert destination_balance.on_hand_qty == pytest.approx(2.0)
    assert destination_balance.available_qty == pytest.approx(2.0)


def test_issue_reserved_stock_consumes_reservation_without_changing_unreserved_availability(services):
    auth = services["auth_service"]
    auth.register_user("inventory-reservation-issuer", "StrongPass123", role_names=["inventory_manager"])
    _site, item, source, _destination = _create_movement_context(services)

    login_as(services, "inventory-reservation-issuer", "StrongPass123")

    stock = services["inventory_stock_service"]
    reservations = services["inventory_reservation_service"]
    stock.post_opening_balance(stock_item_id=item.id, storeroom_id=source.id, quantity=10, unit_cost=4.0)
    reservation = reservations.create_reservation(
        stock_item_id=item.id,
        storeroom_id=source.id,
        reserved_qty=4,
        source_reference_type="work_order",
        source_reference_id="WO-500",
    )

    partial = reservations.issue_reserved_stock(reservation.id, quantity=3, note="Issued first batch")
    mid_balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=source.id)

    assert partial.status.value == "PARTIALLY_ISSUED"
    assert partial.issued_qty == pytest.approx(3.0)
    assert partial.remaining_qty == pytest.approx(1.0)
    assert mid_balance.on_hand_qty == pytest.approx(7.0)
    assert mid_balance.reserved_qty == pytest.approx(1.0)
    assert mid_balance.available_qty == pytest.approx(6.0)

    final = reservations.issue_reserved_stock(reservation.id, quantity=1)
    final_balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=source.id)

    assert final.status.value == "FULLY_ISSUED"
    assert final.issued_qty == pytest.approx(4.0)
    assert final.remaining_qty == pytest.approx(0.0)
    assert final_balance.on_hand_qty == pytest.approx(6.0)
    assert final_balance.reserved_qty == pytest.approx(0.0)
    assert final_balance.available_qty == pytest.approx(6.0)


def test_movement_rules_block_over_issue_and_overconsume_reservation(services):
    auth = services["auth_service"]
    auth.register_user("inventory-movement-rules", "StrongPass123", role_names=["inventory_manager"])
    _site, item, source, _destination = _create_movement_context(services)

    login_as(services, "inventory-movement-rules", "StrongPass123")

    stock = services["inventory_stock_service"]
    reservations = services["inventory_reservation_service"]
    stock.post_opening_balance(stock_item_id=item.id, storeroom_id=source.id, quantity=3)
    reservation = reservations.create_reservation(
        stock_item_id=item.id,
        storeroom_id=source.id,
        reserved_qty=2,
        source_reference_type="task",
        source_reference_id="TASK-300",
    )

    with pytest.raises(ValidationError, match="available quantity negative"):
        stock.issue_stock(stock_item_id=item.id, storeroom_id=source.id, quantity=2)

    with pytest.raises(ValidationError, match="exceeds the reservation remaining quantity"):
        reservations.issue_reserved_stock(reservation.id, quantity=3)
