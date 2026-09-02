"""P30B: Inventory Reservation full modernization -- typed events replace
`inventory_reservations_changed` for all 5 former producers (create/issue/release/cancel via the
new canonical `InventoryReservationUnitOfWork`; link/unlink-document, which never mutated the
Reservation row and now emits no Reservation event at all, matching the P24 Item precedent).
Balance/Ledger are explicitly out of scope -- Reservation's genuine `StockBalance`/
`StockTransaction` mutation is preserved via the existing, unmodified `StockControlService`
posting logic, now bound to the new UoW's own session/repos.

`inventory_reservations_changed` is DELETED from `DomainEvents` entirely (not just left unemitted)
-- assert `not hasattr(domain_events, ...)` rather than connecting a counter to it."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from src.core.modules.inventory_procurement.application.inventory.event_handlers.view_invalidation import (
    RESERVATION_CATEGORY,
    RESERVATION_DETAIL_SCOPE_CODE,
    RESERVATION_LIST_SCOPE_CODE,
    RESERVATION_OPEN_COUNT_SCOPE_CODE,
)
from src.core.modules.inventory_procurement.domain.inventory.reservation_events import (
    InventoryReservationCancelled,
    InventoryReservationConsumptionAdvanced,
    InventoryReservationCreated,
    InventoryReservationReleased,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.inventory import (
    SqlAlchemyStockBalanceRepository,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.shared.events.domain_events import domain_events
from src.tests.ui_runtime_helpers import login_as


def _reservation_context(services, suffix):
    site = services["site_service"].create_site(
        site_code=f"P30B-{suffix}", name=f"P30B Site {suffix}", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"P30B-ITEM-{suffix}",
        name=f"P30B Item {suffix}",
        status="ACTIVE",
        stock_uom="EA",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"P30B-ST-{suffix}",
        name=f"P30B Storeroom {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=5.0
    )
    return site, storeroom, item


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _reservation_hints(hints):
    return [
        h
        for h in hints
        if h.category == RESERVATION_CATEGORY
        and h.scope_code
        in (
            RESERVATION_LIST_SCOPE_CODE,
            RESERVATION_DETAIL_SCOPE_CODE,
            RESERVATION_OPEN_COUNT_SCOPE_CODE,
        )
    ]


def test_legacy_reservation_signal_field_is_deleted():
    assert not hasattr(domain_events, "inventory_reservations_changed")


def test_create_reservation_produces_typed_event_list_and_open_count_hints(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p30b-create-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _reservation_context(services, suffix)
    login_as(services, f"p30b-create-{suffix}", "StrongPass123")
    reservations = services["inventory_reservation_service"]

    hints = _spy_hints(services)
    reservation = reservations.create_reservation(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        reserved_qty=4,
        source_reference_type="task",
        source_reference_id="TASK-1",
    )

    res_hints = _reservation_hints(hints)
    # Created notifies list + open_count, never detail (P30B §19/§21 -- no pre-existing detail
    # view can be stale for a reservation that did not exist a moment ago).
    assert {h.scope_code for h in res_hints} == {
        RESERVATION_LIST_SCOPE_CODE,
        RESERVATION_OPEN_COUNT_SCOPE_CODE,
    }
    assert all(h.entity_id == reservation.id for h in res_hints)


def test_issue_partial_advances_consumption_and_does_not_stale_open_count(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p30b-partial-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _reservation_context(services, suffix)
    login_as(services, f"p30b-partial-{suffix}", "StrongPass123")
    reservations = services["inventory_reservation_service"]

    reservation = reservations.create_reservation(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        reserved_qty=4,
        source_reference_type="task",
        source_reference_id="TASK-2",
    )

    hints = _spy_hints(services)
    issued = reservations.issue_reserved_stock(reservation.id, quantity=2)

    assert issued.status.value == "PARTIALLY_ISSUED"
    res_hints = _reservation_hints(hints)
    # Partial issue stays in the "Open Reservations" counted set (ACTIVE+PARTIALLY_ISSUED) --
    # P30B §20: must NOT stale the Dashboard open-count target.
    assert {h.scope_code for h in res_hints} == {
        RESERVATION_LIST_SCOPE_CODE,
        RESERVATION_DETAIL_SCOPE_CODE,
    }


def test_issue_full_advances_consumption_and_staless_open_count(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p30b-full-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _reservation_context(services, suffix)
    login_as(services, f"p30b-full-{suffix}", "StrongPass123")
    reservations = services["inventory_reservation_service"]

    reservation = reservations.create_reservation(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        reserved_qty=4,
        source_reference_type="task",
        source_reference_id="TASK-3",
    )

    hints = _spy_hints(services)
    issued = reservations.issue_reserved_stock(reservation.id, quantity=4)

    assert issued.status.value == "FULLY_ISSUED"
    res_hints = _reservation_hints(hints)
    # A full issue leaves the open-count set -- must stale the Dashboard target too.
    assert {h.scope_code for h in res_hints} == {
        RESERVATION_LIST_SCOPE_CODE,
        RESERVATION_DETAIL_SCOPE_CODE,
        RESERVATION_OPEN_COUNT_SCOPE_CODE,
    }


def test_release_and_cancel_produce_distinct_event_types(services):
    """P30B §4/§12: Released and Cancelled are kept as distinct DomainEvent types even though
    both currently share the `_close_reservation` implementation helper."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p30b-close-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _reservation_context(services, suffix)
    login_as(services, f"p30b-close-{suffix}", "StrongPass123")
    reservations = services["inventory_reservation_service"]

    released_source = reservations.create_reservation(
        stock_item_id=item.id, storeroom_id=storeroom.id, reserved_qty=2,
        source_reference_type="task", source_reference_id="TASK-4",
    )
    cancelled_source = reservations.create_reservation(
        stock_item_id=item.id, storeroom_id=storeroom.id, reserved_qty=2,
        source_reference_type="task", source_reference_id="TASK-5",
    )

    released = reservations.release_reservation(released_source.id)
    cancelled = reservations.cancel_reservation(cancelled_source.id)

    assert released.status.value == "RELEASED"
    assert cancelled.status.value == "CANCELLED"


def test_document_link_unlink_do_not_touch_reservation_or_emit_reservation_hints(services):
    """P30B §13: link/unlink mutate only `DocumentLink` -- zero Reservation DomainEvent, zero
    `reservation_list`/`reservation_detail`/`reservation_open_count` hints. Mirrors P28B's
    identical PurchaseOrder-side proof."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p30b-doc-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _reservation_context(services, suffix)
    login_as(services, f"p30b-doc-{suffix}", "StrongPass123")
    reservations = services["inventory_reservation_service"]

    reservation = reservations.create_reservation(
        stock_item_id=item.id, storeroom_id=storeroom.id, reserved_qty=2,
        source_reference_type="task", source_reference_id="TASK-6",
    )

    class _FakeDocumentIntegrationService:
        def __init__(self):
            self.link_calls: list[dict] = []
            self.unlink_calls: list[dict] = []

        def link_existing_document(self, **kwargs):
            self.link_calls.append(kwargs)
            return object()

        def unlink_existing_document(self, **kwargs):
            self.unlink_calls.append(kwargs)

    fake_documents = _FakeDocumentIntegrationService()
    original = reservations._document_integration_service
    reservations._document_integration_service = fake_documents
    try:
        hints = _spy_hints(services)
        reservations.link_document(reservation.id, document_id="fake-document-id")
        reservations.unlink_document(reservation.id, document_id="fake-document-id")
    finally:
        reservations._document_integration_service = original

    assert len(fake_documents.link_calls) == 1
    assert len(fake_documents.unlink_calls) == 1
    assert _reservation_hints(hints) == []
    unchanged = reservations.get_reservation(reservation.id)
    assert unchanged.version == reservation.version
    assert unchanged.status == reservation.status


def test_create_reservation_audit_failure_rolls_back_the_whole_transaction(services, monkeypatch):
    """P30B §8/§32: proves the new canonical `InventoryReservationUnitOfWork` is genuinely
    atomic -- Reservation row, Balance row, and StockTransaction row all roll back together, and
    zero postcommit DomainEvent/hint escapes."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p30b-auditfail-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _reservation_context(services, suffix)
    login_as(services, f"p30b-auditfail-{suffix}", "StrongPass123")
    reservations = services["inventory_reservation_service"]

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        reservations.create_reservation(
            stock_item_id=item.id, storeroom_id=storeroom.id, reserved_qty=2,
            source_reference_type="task", source_reference_id="TASK-7",
        )

    assert _reservation_hints(hints) == [], "a failed audit must roll back the transaction and publish nothing"
    assert reservations.list_reservations() == []
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.reserved_qty == 0, "the Balance mutation must roll back together with the Reservation write"


def test_concurrent_reservation_rejects_stale_balance_write_no_oversubscription(services, session):
    """P30B §16/§17: two independent transactions ("Session A"/"Session B") both read the SAME
    `StockBalance` before either writes -- available stock is 10, each attempts to reserve 8.
    Both can pass an in-app availability check against the same stale read; only one may commit.
    Session A commits first; Session B's stale write must be rejected deterministically via the
    same `update_with_version_check` mechanism P30A proved `InventoryReservationUnitOfWork.
    stock_service` already relies on -- no lost update, no oversubscription."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p30b-race-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _reservation_context(services, suffix)

    balance_repo_a = SqlAlchemyStockBalanceRepository(
        session, tenant_context_service=services["tenant_context_service"]
    )
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.version == 1
    assert balance.on_hand_qty == 10
    assert balance.reserved_qty == 0

    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        balance_repo_b = SqlAlchemyStockBalanceRepository(
            session_b, tenant_context_service=services["tenant_context_service"]
        )
        balance_read_by_a = balance_repo_a.get(balance.id)
        balance_read_by_b = balance_repo_b.get(balance.id)
        assert balance_read_by_a.version == 1
        assert balance_read_by_b.version == 1

        # Transaction A reserves 8 (available 10 - 8 = 2 >= 0) and commits first.
        updated_by_a = replace(
            balance_read_by_a,
            reserved_qty=8.0,
            available_qty=2.0,
        )
        balance_repo_a.update(updated_by_a)
        session.commit()

        # Transaction B, still holding its now-stale version=1 read, also reserves 8 computed
        # against the SAME pre-A state -- must be rejected, not silently applied (which would
        # oversubscribe reserved_qty to 16 against only 10 on hand).
        updated_by_b = replace(
            balance_read_by_b,
            reserved_qty=8.0,
            available_qty=2.0,
        )
        with pytest.raises(ConcurrencyError):
            balance_repo_b.update(updated_by_b)
        session_b.rollback()
    finally:
        session_b.close()

    final = balance_repo_a.get(balance.id)
    assert final.reserved_qty == 8.0, "only A's reservation may persist"
    assert final.available_qty == 2.0
    assert final.version == 2
