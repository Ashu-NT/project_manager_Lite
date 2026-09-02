"""P32B: Inventory Cycle Count full modernization -- `schedule_cycle_count` converges onto the
canonical `InventoryFoundationUnitOfWork` (gaining, for the first time, an atomic enterprise audit
of its own), and both `schedule_cycle_count`/`complete_cycle_count` record typed
`InventoryCycleCountScheduled`/`InventoryCycleCountCompleted` DomainEvents in place of the legacy
`inventory_cycle_counts_changed` Signal. `inventory_cycle_counts_changed` is DELETED from
`DomainEvents` entirely (not just left unemitted) -- assert `not hasattr(domain_events, ...)`.

`cycle_count_list`/`cycle_count_detail` are Cycle Count's own two ViewInvalidation projections,
owned exclusively by the Inventory(Foundation) workspace. Scheduled invalidates list only (a
brand-new row cannot have a stale pre-existing detail view open); Completed invalidates both.
The 5 incidental legacy subscriptions (Catalog/Pricing/Procurement/Dashboard/Reservations) are
proven to have zero reaction to a Cycle Count mutation."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.inventory_procurement.application.inventory.event_handlers.view_invalidation import (
    CYCLE_COUNT_CATEGORY,
    CYCLE_COUNT_DETAIL_SCOPE_CODE,
    CYCLE_COUNT_LIST_SCOPE_CODE,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.tests.ui_runtime_helpers import login_as


def _procurement_context(services, suffix):
    site = services["site_service"].create_site(
        site_code=f"P32B-{suffix}", name=f"P32B Site {suffix}", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"P32B-ITEM-{suffix}",
        name=f"P32B Item {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"P32B-ST-{suffix}", name=f"P32B Storeroom {suffix}", site_id=site.id, status="ACTIVE"
    )
    return site, storeroom, item


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


def _cycle_count_hints(hints):
    return [h for h in hints if h.category == CYCLE_COUNT_CATEGORY]


def test_legacy_cycle_count_signal_field_is_deleted():
    assert not hasattr(domain_events, "inventory_cycle_counts_changed")


# ---------------------------------------------------------------------------
# Schedule -> list-only hint
# ---------------------------------------------------------------------------


def test_schedule_cycle_count_produces_list_only_hint(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p32b-sched-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p32b-sched-{suffix}", "StrongPass123")

    hints = _spy_hints(services)
    cycle_count = services["inventory_foundation_service"].schedule_cycle_count(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    cc_hints = _cycle_count_hints(hints)
    assert {h.scope_code for h in cc_hints} == {CYCLE_COUNT_LIST_SCOPE_CODE}
    assert all(h.entity_id == cycle_count.id for h in cc_hints)


def test_schedule_cycle_count_audit_failure_rolls_back_creation(services, monkeypatch):
    """P32B: schedule previously had zero atomic enterprise audit at all -- gains one here, atomic
    with the CycleCount write. Proven by a monkeypatched audit-backend failure rolling back the
    creation entirely, matching the same governance-upgrade proof P24/P30B/P31B each provided for
    their own first-modernized path."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p32b-schedfail-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p32b-schedfail-{suffix}", "StrongPass123")

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        services["inventory_foundation_service"].schedule_cycle_count(
            stock_item_id=item.id, storeroom_id=storeroom.id
        )

    assert _cycle_count_hints(hints) == []
    remaining = services["inventory_foundation_service"].list_cycle_counts(storeroom_id=storeroom.id)
    assert remaining == [], "a failed audit must roll back the CycleCount creation too"


# ---------------------------------------------------------------------------
# Complete -> list + detail hint (zero variance: no Balance event; nonzero: Balance event too)
# ---------------------------------------------------------------------------


def test_complete_cycle_count_zero_variance_produces_list_and_detail_hint_no_balance_event(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p32b-cc0-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p32b-cc0-{suffix}", "StrongPass123")
    foundation = services["inventory_foundation_service"]
    cycle_count = foundation.schedule_cycle_count(stock_item_id=item.id, storeroom_id=storeroom.id)

    hints = _spy_hints(services)
    foundation.complete_cycle_count(cycle_count.id, counted_qty=10)

    cc_hints = _cycle_count_hints(hints)
    assert {h.scope_code for h in cc_hints} == {CYCLE_COUNT_LIST_SCOPE_CODE, CYCLE_COUNT_DETAIL_SCOPE_CODE}
    assert all(h.entity_id == cycle_count.id for h in cc_hints)
    balance_hints = [h for h in hints if h.category == "inventory_balance"]
    assert balance_hints == [], "counting stock with zero variance must not mutate/notify Balance"


def test_complete_cycle_count_nonzero_variance_produces_both_cycle_count_and_balance_hints(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p32b-cc1-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p32b-cc1-{suffix}", "StrongPass123")
    foundation = services["inventory_foundation_service"]
    cycle_count = foundation.schedule_cycle_count(stock_item_id=item.id, storeroom_id=storeroom.id)

    hints = _spy_hints(services)
    foundation.complete_cycle_count(cycle_count.id, counted_qty=7)

    cc_hints = _cycle_count_hints(hints)
    assert {h.scope_code for h in cc_hints} == {CYCLE_COUNT_LIST_SCOPE_CODE, CYCLE_COUNT_DETAIL_SCOPE_CODE}
    balance_hints = [h for h in hints if h.category == "inventory_balance"]
    assert balance_hints, "a nonzero variance must still produce its own StockOnHandQuantityChanged fact"
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_hand_qty == 7.0


# ---------------------------------------------------------------------------
# Concurrency -- stale version rollback, zero events
# ---------------------------------------------------------------------------


def test_complete_cycle_count_stale_version_rolls_back_with_zero_hints(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p32b-stale-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p32b-stale-{suffix}", "StrongPass123")
    foundation = services["inventory_foundation_service"]
    cycle_count = foundation.schedule_cycle_count(stock_item_id=item.id, storeroom_id=storeroom.id)

    hints = _spy_hints(services)
    with pytest.raises(ConcurrencyError):
        foundation.complete_cycle_count(cycle_count.id, counted_qty=7, expected_version=cycle_count.version + 1)

    assert _cycle_count_hints(hints) == []
    balance_hints = [h for h in hints if h.category == "inventory_balance"]
    assert balance_hints == []


# ---------------------------------------------------------------------------
# Consumer cutover -- incidental (Catalog/Pricing/Procurement/Dashboard/Reservations) vs genuine
# (Inventory(Foundation))
# ---------------------------------------------------------------------------


def test_incidental_consumers_have_zero_cycle_count_reaction(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p32b-incid-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p32b-incid-{suffix}", "StrongPass123")
    catalog = _pm_catalog(services)
    calls: list[str] = []
    catalog._catalog_workspace.refresh = lambda: calls.append("catalog")
    catalog._pricing_workspace._request_domain_refresh = lambda: calls.append("pricing")
    catalog._procurement_workspace._request_domain_refresh = lambda: calls.append("procurement")
    catalog._dashboard_workspace._request_domain_refresh = lambda: calls.append("dashboard")
    catalog._reservations_workspace._request_domain_refresh = lambda: calls.append("reservations")

    services["inventory_foundation_service"].schedule_cycle_count(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert calls == [], (
        "Catalog, Pricing, Procurement, Dashboard, and Reservations must never react to a Cycle "
        "Count mutation (zero real dependency)"
    )


def test_inventory_foundation_workspace_reacts_to_cycle_count_mutation(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p32b-genuine-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item = _procurement_context(services, suffix)
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id, storeroom_id=storeroom.id, quantity=10, unit_cost=1.0
    )
    login_as(services, f"p32b-genuine-{suffix}", "StrongPass123")
    catalog = _pm_catalog(services)
    calls: list[str] = []
    catalog._inventory_workspace._request_domain_refresh = lambda: calls.append("inventory")

    services["inventory_foundation_service"].schedule_cycle_count(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert calls, "Inventory(Foundation) workspace must react to a Cycle Count Scheduled event"
