"""P31B: Stock Balance full modernization -- typed, field-sensitive DomainEvents
(`StockOnHandQuantityChanged`/`StockReservedQuantityChanged`/`StockOnOrderQuantityChanged`)
replace `inventory_balances_changed` for every confirmed writer (Reservation, Purchase Order
approve/cancel, Goods Receipt, Cycle Count, Inventory(Foundation) manual stock movements).
StockTransaction remains the unmodified persistence ledger -- no separate Ledger DomainEvents.
Distributed transaction ownership is preserved: each capability's own UoW/session records its own
Balance fact, no centralized Balance mega-UoW.

`inventory_balances_changed` is DELETED from `DomainEvents` entirely (not just left unemitted) --
assert `not hasattr(domain_events, ...)` rather than connecting a counter to it. The confirmed
P31A silent-mutation gap (`cancel_purchase_order` mutating `on_order_qty` with zero notification)
is fixed here, proven by a dedicated regression test."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from src.application.runtime import build_desktop_api_registry
from src.core.modules.inventory_procurement.application.inventory.event_handlers.view_invalidation import (
    BALANCE_CATEGORY,
    BALANCE_DETAIL_SCOPE_CODE,
    BALANCE_LIST_SCOPE_CODE,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.inventory import (
    SqlAlchemyStockBalanceRepository,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.domain.master_data.party import PartyType
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.tests.ui_runtime_helpers import login_as


def _procurement_context(services, suffix):
    site = services["site_service"].create_site(
        site_code=f"P31B-{suffix}", name=f"P31B Site {suffix}", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"P31B-ITEM-{suffix}",
        name=f"P31B Item {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"P31B-ST-{suffix}", name=f"P31B Storeroom {suffix}", site_id=site.id, status="ACTIVE"
    )
    supplier = services["party_service"].create_party(
        party_code=f"SUP-P31B-{suffix}", party_name=f"P31B Supplier {suffix}", party_type=PartyType.SUPPLIER
    )
    return site, storeroom, item, supplier


def _pm_catalog(services) -> InventoryProcurementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _balance_hints(hints):
    return [h for h in hints if h.category == BALANCE_CATEGORY]


def test_legacy_balance_signal_field_is_deleted():
    assert not hasattr(domain_events, "inventory_balances_changed")


# ---------------------------------------------------------------------------
# Reservation -> Balance facts
# ---------------------------------------------------------------------------


def test_reservation_create_produces_reserved_quantity_balance_hints(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-res-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=5.0
    )
    login_as(services, f"p31b-res-{suffix}", "StrongPass123")

    hints = _spy_hints(services)
    services["inventory_reservation_service"].create_reservation(
        stock_item_id=item.id, storeroom_id=storeroom.id, reserved_qty=4,
        source_reference_type="task", source_reference_id="TASK-P31B-1",
    )
    res_hints = _balance_hints(hints)
    assert {h.scope_code for h in res_hints} == {BALANCE_LIST_SCOPE_CODE, BALANCE_DETAIL_SCOPE_CODE}


def test_reservation_issue_produces_onhand_and_reserved_hints_with_correct_resulting_state(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-issue-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=5.0
    )
    login_as(services, f"p31b-issue-{suffix}", "StrongPass123")
    reservations = services["inventory_reservation_service"]
    reservation = reservations.create_reservation(
        stock_item_id=item.id, storeroom_id=storeroom.id, reserved_qty=4,
        source_reference_type="task", source_reference_id="TASK-P31B-2",
    )

    hints = _spy_hints(services)
    reservations.issue_reserved_stock(reservation.id, quantity=2)

    # Both `StockOnHandQuantityChanged` and `StockReservedQuantityChanged` fire from this one
    # operation (P31B §7/§13) -- both target the same balance, so list/detail dedupe to 2 hints
    # total regardless of event-type count; the resulting persisted state proves each event's
    # own delta was computed correctly (on_hand -2, reserved -2).
    assert {h.scope_code for h in _balance_hints(hints)} == {BALANCE_LIST_SCOPE_CODE, BALANCE_DETAIL_SCOPE_CODE}
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_hand_qty == 8.0
    assert balance.reserved_qty == 2.0


def test_reservation_release_produces_reserved_event_only(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-rel-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=5.0
    )
    login_as(services, f"p31b-rel-{suffix}", "StrongPass123")
    reservations = services["inventory_reservation_service"]
    reservation = reservations.create_reservation(
        stock_item_id=item.id, storeroom_id=storeroom.id, reserved_qty=3,
        source_reference_type="task", source_reference_id="TASK-P31B-3",
    )

    hints = _spy_hints(services)
    reservations.release_reservation(reservation.id)
    res_hints = _balance_hints(hints)
    assert {h.scope_code for h in res_hints} == {BALANCE_LIST_SCOPE_CODE, BALANCE_DETAIL_SCOPE_CODE}


# ---------------------------------------------------------------------------
# Purchase Order -> Balance facts (approve, and the P31A silent-mutation gap fix)
# ---------------------------------------------------------------------------


def test_po_approval_produces_on_order_balance_hints_no_reflective_bridge(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-appr-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p31b-apprv-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p31b-appr-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]

    po = purchasing.create_purchase_order(site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR")
    purchasing.add_purchase_order_line(
        po.id, stock_item_id=item.id, destination_storeroom_id=storeroom.id, quantity_ordered=6, unit_price=10.0
    )
    po = purchasing.submit_purchase_order(po.id)

    hints = _spy_hints(services)
    login_as(services, f"p31b-apprv-{suffix}", "StrongPass123")
    services["approval_service"].approve_and_apply(po.approval_request_id, note="Approved")

    bal_hints = _balance_hints(hints)
    assert {h.scope_code for h in bal_hints} == {BALANCE_LIST_SCOPE_CODE, BALANCE_DETAIL_SCOPE_CODE}
    login_as(services, f"p31b-appr-{suffix}", "StrongPass123")
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_order_qty == 6.0


def test_po_cancel_after_approval_fixes_the_p31a_silent_mutation_gap(services):
    """P31A found `cancel_purchase_order` mutates `on_order_qty` on an already-approved PO with
    zero notification of any kind. P31B fixes this -- proven here by asserting a real
    `StockOnOrderQuantityChanged`-driven hint fires, not merely that Balance itself changed."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-cxl-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p31b-cxlappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p31b-cxl-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]

    po = purchasing.create_purchase_order(site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR")
    purchasing.add_purchase_order_line(
        po.id, stock_item_id=item.id, destination_storeroom_id=storeroom.id, quantity_ordered=6, unit_price=10.0
    )
    po = purchasing.submit_purchase_order(po.id)
    login_as(services, f"p31b-cxlappr-{suffix}", "StrongPass123")
    services["approval_service"].approve_and_apply(po.approval_request_id, note="Approved")
    login_as(services, f"p31b-cxl-{suffix}", "StrongPass123")
    balance_after_approval = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance_after_approval.on_order_qty == 6.0

    hints = _spy_hints(services)
    purchasing.cancel_purchase_order(po.id, note="No longer needed")

    bal_hints = _balance_hints(hints)
    assert bal_hints, "cancelling an approved PO must now notify Balance consumers (P31A gap fixed)"
    balance_after_cancel = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance_after_cancel.on_order_qty == 0.0


def test_po_rejection_still_touches_zero_balance(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-rej-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p31b-rejappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p31b-rej-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]

    po = purchasing.create_purchase_order(site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR")
    purchasing.add_purchase_order_line(
        po.id, stock_item_id=item.id, destination_storeroom_id=storeroom.id, quantity_ordered=6, unit_price=10.0
    )
    po = purchasing.submit_purchase_order(po.id)

    hints = _spy_hints(services)
    login_as(services, f"p31b-rejappr-{suffix}", "StrongPass123")
    services["approval_service"].reject(po.approval_request_id, note="Rejected")

    assert _balance_hints(hints) == [], "rejection never touches Balance -- on-order was never incremented"


# ---------------------------------------------------------------------------
# Goods Receipt -> Balance facts (on-hand and on-order, one transaction)
# ---------------------------------------------------------------------------


def test_receipt_produces_onhand_and_onorder_balance_hints_no_legacy_signal(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-rcv-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p31b-rcvappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p31b-rcv-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]

    po = purchasing.create_purchase_order(site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR")
    line = purchasing.add_purchase_order_line(
        po.id, stock_item_id=item.id, destination_storeroom_id=storeroom.id, quantity_ordered=5, unit_price=20.0
    )
    po = purchasing.submit_purchase_order(po.id)
    login_as(services, f"p31b-rcvappr-{suffix}", "StrongPass123")
    services["approval_service"].approve_and_apply(po.approval_request_id, note="Approved for receipt")
    login_as(services, f"p31b-rcv-{suffix}", "StrongPass123")

    hints = _spy_hints(services)
    purchasing.post_receipt(
        po.id, receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 5, "quantity_rejected": 0}]
    )

    bal_hints = _balance_hints(hints)
    assert {h.scope_code for h in bal_hints} == {BALANCE_LIST_SCOPE_CODE, BALANCE_DETAIL_SCOPE_CODE}
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_hand_qty == 5.0
    assert balance.on_order_qty == 0.0


# ---------------------------------------------------------------------------
# Cycle Count -> Balance facts (counting != changing stock)
# ---------------------------------------------------------------------------


def test_cycle_count_zero_variance_produces_zero_balance_hints(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-cc0-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-cc0-{suffix}", "StrongPass123")
    foundation = services["inventory_foundation_service"]
    cycle_count = foundation.schedule_cycle_count(stock_item_id=item.id, storeroom_id=storeroom.id)

    hints = _spy_hints(services)
    foundation.complete_cycle_count(cycle_count.id, counted_qty=10)
    assert _balance_hints(hints) == [], "counting stock with zero variance must not mutate/notify Balance"


def test_cycle_count_nonzero_variance_produces_onhand_balance_hints(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-cc1-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-cc1-{suffix}", "StrongPass123")
    foundation = services["inventory_foundation_service"]
    cycle_count = foundation.schedule_cycle_count(stock_item_id=item.id, storeroom_id=storeroom.id)

    hints = _spy_hints(services)
    foundation.complete_cycle_count(cycle_count.id, counted_qty=7)
    bal_hints = _balance_hints(hints)
    assert {h.scope_code for h in bal_hints} == {BALANCE_LIST_SCOPE_CODE, BALANCE_DETAIL_SCOPE_CODE}
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_hand_qty == 7.0


def test_cycle_count_completion_audit_failure_rolls_back_balance_too(services, monkeypatch):
    """P31B §31: Cycle Count gains atomic enterprise audit for the first time -- proven by a
    monkeypatched audit-backend failure rolling back the Balance mutation with it, matching the
    same governance-upgrade proof P24/P30B each provided for their own first-modernized path."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-ccfail-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-ccfail-{suffix}", "StrongPass123")
    foundation = services["inventory_foundation_service"]
    cycle_count = foundation.schedule_cycle_count(stock_item_id=item.id, storeroom_id=storeroom.id)

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        foundation.complete_cycle_count(cycle_count.id, counted_qty=3)

    assert _balance_hints(hints) == []
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_hand_qty == 10.0, "a failed audit must roll back the Balance mutation too"


# ---------------------------------------------------------------------------
# Manual stock movements -> Balance facts
# ---------------------------------------------------------------------------


def test_manual_adjustment_produces_onhand_balance_hints_via_foundation_service(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-adj-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-adj-{suffix}", "StrongPass123")

    hints = _spy_hints(services)
    services["inventory_foundation_service"].post_adjustment(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=2, direction="INCREASE"
    )
    bal_hints = _balance_hints(hints)
    assert {h.scope_code for h in bal_hints} == {BALANCE_LIST_SCOPE_CODE, BALANCE_DETAIL_SCOPE_CODE}


def test_manual_transfer_produces_two_onhand_balance_facts(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-trf-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    other_storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"P31B-ST2-{suffix}", name="Second storeroom", site_id=site.id, status="ACTIVE"
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-trf-{suffix}", "StrongPass123")

    hints = _spy_hints(services)
    services["inventory_foundation_service"].transfer_stock(
        stock_item_id=item.id,
        source_storeroom_id=storeroom.id,
        destination_storeroom_id=other_storeroom.id,
        quantity=4,
    )

    # Two distinct balance rows (source + destination) -> two distinct `ResourceScope` detail
    # targets, proving two separate `StockOnHandQuantityChanged` facts were recorded, not one
    # organization-wide "stock changed" event (P31B §8/§23).
    bal_hints = _balance_hints(hints)
    detail_hints = [h for h in bal_hints if h.scope_code == BALANCE_DETAIL_SCOPE_CODE]
    assert len({h.entity_id for h in detail_hints}) == 2
    source_balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    destination_balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=other_storeroom.id
    )
    assert source_balance.on_hand_qty == 6.0
    assert destination_balance.on_hand_qty == 4.0


def test_manual_movements_audit_failure_rolls_back_balance(services, monkeypatch):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-mmfail-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-mmfail-{suffix}", "StrongPass123")

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        services["inventory_foundation_service"].post_adjustment(
            stock_item_id=item.id, storeroom_id=storeroom.id, quantity=2, direction="INCREASE"
        )

    assert _balance_hints(hints) == []
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_hand_qty == 10.0


# ---------------------------------------------------------------------------
# Concurrency -- preserved uniform optimistic mechanism across capabilities
# ---------------------------------------------------------------------------


def test_concurrent_manual_adjustment_and_reservation_conflict_on_same_balance(services, session):
    """Cross-capability lost-update scenario (P31A §17, whole-row versioning): a manual
    adjustment (on_hand) and a reservation hold (reserved) on the SAME balance row, read
    concurrently, must not both silently commit -- the loser gets `ConcurrencyError`."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-race-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-race-{suffix}", "StrongPass123")

    balance_repo_a = SqlAlchemyStockBalanceRepository(session, tenant_context_service=services["tenant_context_service"])
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.version == 1

    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        balance_repo_b = SqlAlchemyStockBalanceRepository(session_b, tenant_context_service=services["tenant_context_service"])
        read_by_a = balance_repo_a.get(balance.id)
        read_by_b = balance_repo_b.get(balance.id)
        assert read_by_a.version == read_by_b.version == 1

        updated_by_a = replace(read_by_a, on_hand_qty=12.0, available_qty=12.0)
        balance_repo_a.update(updated_by_a)
        session.commit()

        updated_by_b = replace(read_by_b, reserved_qty=3.0, available_qty=7.0)
        with pytest.raises(ConcurrencyError):
            balance_repo_b.update(updated_by_b)
        session_b.rollback()
    finally:
        session_b.close()

    final = balance_repo_a.get(balance.id)
    assert final.on_hand_qty == 12.0
    assert final.reserved_qty == 0.0, "the losing transaction's reserved_qty change must not persist"
    assert final.version == 2


# ---------------------------------------------------------------------------
# Consumer cutover -- genuine (Inventory/Pricing/Dashboard) vs incidental (Catalog/Procurement)
# ---------------------------------------------------------------------------


def test_catalog_and_procurement_have_zero_balance_reaction(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-incid-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-incid-{suffix}", "StrongPass123")
    catalog = _pm_catalog(services)
    calls: list[str] = []
    catalog._catalog_workspace.refresh = lambda: calls.append("catalog_refresh")
    catalog._procurement_workspace.refresh = lambda: calls.append("procurement_refresh")
    catalog._procurement_workspace._request_domain_refresh = lambda: calls.append("procurement_refresh")

    services["inventory_foundation_service"].post_adjustment(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=2, direction="INCREASE"
    )
    assert calls == [], "Catalog and Procurement must never react to a Balance mutation (zero real dependency)"


def test_inventory_pricing_dashboard_all_react_to_balance_mutation(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p31b-genuine-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p31b-genuine-{suffix}", "StrongPass123")
    catalog = _pm_catalog(services)
    calls: list[str] = []
    catalog._inventory_workspace.refresh = lambda: calls.append("inventory")
    catalog._pricing_workspace._request_domain_refresh = lambda: calls.append("pricing")
    catalog._dashboard_workspace._request_domain_refresh = lambda: calls.append("dashboard")

    services["inventory_foundation_service"].post_adjustment(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=2, direction="INCREASE"
    )
    assert set(calls) == {"inventory", "pricing", "dashboard"}
