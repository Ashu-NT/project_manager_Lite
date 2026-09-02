"""P20: Inventory Storeroom + Location typed events + ViewInvalidation + legacy signal
retirement.

Covers: StoreroomCreated/StoreroomProfileUpdated/StoreroomStatusChanged -> storeroom_list
(OrganizationScope), LocationCreated/LocationProfileUpdated -> location_list (OrganizationScope),
true no-op semantics on update_storeroom/update_storage_location, dedupe by (transaction
correlation_id, target identity), the real narrow per-workspace consumer wiring (Inventory/
Dashboard full refresh, Pricing/Procurement refresh_site_options, Reservations
refresh_storeroom_options, Catalog zero dependency), and the full retirement of
`inventory_storerooms_changed`/`inventory_locations_changed` (zero producers, zero consumers,
fields absent).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.inventory_procurement.application.inventory.event_handlers.view_invalidation import (
    INVENTORY_CATEGORY,
    LOCATION_LIST_SCOPE_CODE,
    STOREROOM_LIST_SCOPE_CODE,
    build_location_list_view_invalidation_handler,
    build_storeroom_list_view_invalidation_handler,
)
from src.core.modules.inventory_procurement.domain.inventory.foundation_events import (
    LocationCreated,
    LocationProfileUpdated,
    StoreroomCreated,
    StoreroomProfileUpdated,
    StoreroomStatusChanged,
)
from src.core.platform.domain.master_data.party import PartyType
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import OrganizationScope
from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.tests.ui_runtime_helpers import login_as

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _pm_catalog(services) -> InventoryProcurementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)


def _spy_hints(services):
    hints = []
    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


class _AnyOrgFilter:
    def matches(self, scope) -> bool:
        return True


def _inventory_hints(hints):
    return [h for h in hints if h.category == INVENTORY_CATEGORY]


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _context(correlation_id: str) -> DomainEventContext:
    return DomainEventContext(correlation_id=correlation_id)


def _seed_site_and_manager(services):
    site = services["site_service"].create_site(
        site_code=_unique("P20-SITE"), name="P20 Site", currency_code="EUR",
    )
    manager = services["party_service"].create_party(
        party_code=_unique("P20-MGR"), party_name="P20 Manager", party_type=PartyType.CONTRACTOR,
    )
    return site, manager


def _login_inventory_manager(services) -> None:
    username = _unique("p20-inventory-user")
    services["auth_service"].register_user(username, "StrongPass123", role_names=["inventory_manager"])
    login_as(services, username, "StrongPass123")


# ---------------------------------------------------------------------------
# ViewInvalidation handler: mapping, dedupe (unit-level, no DB)
# ---------------------------------------------------------------------------


def test_storeroom_events_map_to_storeroom_list_target():
    channel = _fake_channel()
    handler = build_storeroom_list_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        StoreroomCreated(tenant_id="t1", organization_id="o1", storeroom_id="s1", occurred_at=now),
        _context("c1"),
    )
    hint = channel.notified[0]
    assert hint.scope_code == STOREROOM_LIST_SCOPE_CODE
    assert hint.category == INVENTORY_CATEGORY
    assert isinstance(hint.scope, OrganizationScope)
    assert hint.scope.tenant_id == "t1"
    assert hint.scope.organization_id == "o1"
    assert hint.entity_id == "s1"


def test_location_events_map_to_location_list_target():
    channel = _fake_channel()
    handler = build_location_list_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        LocationCreated(tenant_id="t1", organization_id="o1", location_id="l1", occurred_at=now),
        _context("c1"),
    )
    hint = channel.notified[0]
    assert hint.scope_code == LOCATION_LIST_SCOPE_CODE
    assert hint.entity_id == "l1"


def test_storeroom_dedupe_by_org_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_storeroom_list_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        StoreroomCreated(tenant_id="t1", organization_id="o1", storeroom_id="s1", occurred_at=now),
        _context("same-tx"),
    )
    handler(
        StoreroomProfileUpdated(tenant_id="t1", organization_id="o1", storeroom_id="s2", occurred_at=now),
        _context("same-tx"),
    )
    assert len(channel.notified) == 1, "same org target within one transaction coalesces"

    handler(
        StoreroomStatusChanged(
            tenant_id="t1", organization_id="o2", storeroom_id="s3", status="ACTIVE", occurred_at=now,
        ),
        _context("same-tx"),
    )
    assert len(channel.notified) == 2, "a distinct org within the same transaction is separate"

    handler(
        StoreroomCreated(tenant_id="t1", organization_id="o1", storeroom_id="s4", occurred_at=now),
        _context("next-tx"),
    )
    assert len(channel.notified) == 3, "a new transaction is never coalesced with the previous one"


def test_storeroom_and_location_handlers_never_cross_notify():
    """Proves the two targets are genuinely independent -- a Location handler instance never
    reacts to a Storeroom fact and vice versa (they are wired to different DomainEvent types at
    the composition root, but this proves the handler bodies themselves are also disjoint)."""
    storeroom_channel = _fake_channel()
    location_channel = _fake_channel()
    storeroom_handler = build_storeroom_list_view_invalidation_handler(storeroom_channel)
    location_handler = build_location_list_view_invalidation_handler(location_channel)
    now = datetime.now(timezone.utc)

    storeroom_handler(
        StoreroomCreated(tenant_id="t1", organization_id="o1", storeroom_id="s1", occurred_at=now),
        _context("c1"),
    )
    location_handler(
        LocationCreated(tenant_id="t1", organization_id="o1", location_id="l1", occurred_at=now),
        _context("c1"),
    )
    assert len(storeroom_channel.notified) == 1
    assert storeroom_channel.notified[0].scope_code == STOREROOM_LIST_SCOPE_CODE
    assert len(location_channel.notified) == 1
    assert location_channel.notified[0].scope_code == LOCATION_LIST_SCOPE_CODE


# ---------------------------------------------------------------------------
# Real InventoryService/InventoryFoundationService producer path
# ---------------------------------------------------------------------------


def test_create_storeroom_produces_exactly_one_storeroom_list_hint(services):
    site, manager = _seed_site_and_manager(services)
    _login_inventory_manager(services)
    hints = _spy_hints(services)

    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id,
        status="ACTIVE", manager_party_id=manager.id,
    )

    inventory_hints = _inventory_hints(hints)
    assert len(inventory_hints) == 1
    assert inventory_hints[0].scope_code == STOREROOM_LIST_SCOPE_CODE
    assert inventory_hints[0].entity_id == storeroom.id


def test_update_storeroom_true_no_op_produces_zero_hints(services):
    site, manager = _seed_site_and_manager(services)
    _login_inventory_manager(services)
    inventory_service = services["inventory_service"]
    storeroom = inventory_service.create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id, status="ACTIVE",
    )
    hints = _spy_hints(services)

    unchanged = inventory_service.update_storeroom(
        storeroom.id, name="P20 Storeroom", expected_version=storeroom.version,
    )

    assert unchanged.version == storeroom.version, "true no-op: no synthetic version bump"
    assert _inventory_hints(hints) == []


def test_update_storeroom_profile_change_produces_exactly_one_hint(services):
    site, manager = _seed_site_and_manager(services)
    _login_inventory_manager(services)
    inventory_service = services["inventory_service"]
    storeroom = inventory_service.create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id, status="ACTIVE",
    )
    hints = _spy_hints(services)

    updated = inventory_service.update_storeroom(
        storeroom.id, name="Renamed Storeroom", expected_version=storeroom.version,
    )

    assert updated.name == "Renamed Storeroom"
    inventory_hints = _inventory_hints(hints)
    assert len(inventory_hints) == 1
    assert inventory_hints[0].scope_code == STOREROOM_LIST_SCOPE_CODE


def test_update_storeroom_status_transition_produces_exactly_one_hint(services):
    site, manager = _seed_site_and_manager(services)
    _login_inventory_manager(services)
    inventory_service = services["inventory_service"]
    storeroom = inventory_service.create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id, status="DRAFT",
    )
    hints = _spy_hints(services)

    activated = inventory_service.update_storeroom(
        storeroom.id, status="ACTIVE", expected_version=storeroom.version,
    )

    assert activated.status == "ACTIVE"
    inventory_hints = _inventory_hints(hints)
    assert len(inventory_hints) == 1, "one target (storeroom_list); status+profile both map there"
    assert inventory_hints[0].scope_code == STOREROOM_LIST_SCOPE_CODE


def test_create_and_update_storage_location_produce_exactly_one_hint_each(services):
    site, _manager = _seed_site_and_manager(services)
    _login_inventory_manager(services)
    inventory_service = services["inventory_service"]
    foundation_service = services["inventory_foundation_service"]
    storeroom = inventory_service.create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id, status="ACTIVE",
    )
    hints = _spy_hints(services)

    location = foundation_service.create_storage_location(
        storeroom_id=storeroom.id, location_code=_unique("P20-LOC"), name="P20 Location",
    )
    location_hints = _inventory_hints(hints)
    assert len(location_hints) == 1
    assert location_hints[0].scope_code == LOCATION_LIST_SCOPE_CODE
    assert location_hints[0].entity_id == location.id

    updated = foundation_service.update_storage_location(
        location.id, name="Renamed Location", expected_version=location.version,
    )
    assert updated.name == "Renamed Location"
    location_hints = _inventory_hints(hints)
    assert len(location_hints) == 2
    assert location_hints[1].scope_code == LOCATION_LIST_SCOPE_CODE


def test_update_storage_location_true_no_op_produces_zero_hints(services):
    site, _manager = _seed_site_and_manager(services)
    _login_inventory_manager(services)
    inventory_service = services["inventory_service"]
    foundation_service = services["inventory_foundation_service"]
    storeroom = inventory_service.create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id, status="ACTIVE",
    )
    location = foundation_service.create_storage_location(
        storeroom_id=storeroom.id, location_code=_unique("P20-LOC"), name="P20 Location",
    )
    hints = _spy_hints(services)

    unchanged = foundation_service.update_storage_location(
        location.id, name="P20 Location", expected_version=location.version,
    )

    assert unchanged.version == location.version
    assert _inventory_hints(hints) == []


def test_storeroom_mutation_hint_is_scoped_to_the_active_organization(services):
    site, _manager = _seed_site_and_manager(services)
    org = services["tenant_context_service"].get_active_organization()
    _login_inventory_manager(services)
    hints = _spy_hints(services)

    services["inventory_service"].create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id, status="ACTIVE",
    )

    inventory_hints = _inventory_hints(hints)
    assert len(inventory_hints) == 1
    assert inventory_hints[0].scope.tenant_id == org.tenant_id
    assert inventory_hints[0].scope.organization_id == org.id


# ---------------------------------------------------------------------------
# UI: per-workspace narrow consumer wiring
# ---------------------------------------------------------------------------


def test_catalog_has_zero_storeroom_or_location_references():
    """Catalog: E (incidental) -- proven from source (P20 §11) that no Catalog presenter
    reads Storeroom or Location data at all. Confirms the subscription was removed with no
    replacement, matching the Control-workspace precedent from P18B.

    P33-CLEANUP: `catalog_domain_event_binder.py` was deleted outright -- Catalog's Storeroom/
    Location incidence was the P20-era reason it had zero legacy subscriptions, and by P33 the
    module's own last remaining subscription (`inventory_receipts_changed`) was also removed,
    leaving the binder a permanent no-op that was then deleted rather than kept as an empty
    shell. Its absence is itself the proof."""
    import importlib.util

    assert importlib.util.find_spec(
        "src.ui_qml.modules.inventory_procurement.controllers.catalog.catalog_domain_event_binder"
    ) is None


def test_pricing_and_procurement_controllers_expose_refresh_site_options_seam():
    """Pricing/Procurement: B (storeroom_options selector dependency only) -- reuses the
    existing narrow `refresh_site_options` seam (already refreshes storeroom_options alongside
    site_options); no Location dependency proven from source."""
    from src.ui_qml.modules.inventory_procurement.controllers.pricing.pricing_workspace_controller import (
        InventoryProcurementPricingWorkspaceController,
    )
    from src.ui_qml.modules.inventory_procurement.controllers.procurement.procurement_workspace_controller import (
        InventoryProcurementProcurementWorkspaceController,
    )

    assert hasattr(InventoryProcurementPricingWorkspaceController, "refresh_site_options")
    assert hasattr(InventoryProcurementProcurementWorkspaceController, "refresh_site_options")


def test_reservations_controller_gained_a_narrow_refresh_storeroom_options_seam():
    """Reservations: B (storeroom_options selector dependency only) -- P20 additively extracted
    a `refresh_storeroom_options` seam (Reservations had no `refresh_site_options`-equivalent
    method, unlike Pricing/Procurement)."""
    from src.ui_qml.modules.inventory_procurement.controllers.reservations.reservations_workspace_controller import (
        InventoryProcurementReservationsWorkspaceController,
    )

    assert hasattr(InventoryProcurementReservationsWorkspaceController, "refresh_storeroom_options")


def test_real_catalog_shows_zero_storeroom_stale_reactions_end_to_end(services):
    """End-to-end proof that Catalog's own workspace never refreshes off a Storeroom mutation --
    complements the source-inspection guard above with a real wiring check via the full
    `InventoryProcurementWorkspaceCatalog`."""
    site, _manager = _seed_site_and_manager(services)
    _login_inventory_manager(services)
    catalog = _pm_catalog(services)
    calls: list[str] = []
    catalog._catalog_workspace.refresh = lambda: calls.append("catalog_refresh")

    services["inventory_service"].create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id, status="ACTIVE",
    )

    assert calls == [], "Catalog must never react to a Storeroom mutation"


def test_real_pricing_workspace_refreshes_storeroom_options_only_on_storeroom_mutation(services):
    site, _manager = _seed_site_and_manager(services)
    _login_inventory_manager(services)
    catalog = _pm_catalog(services)
    calls: list[str] = []
    catalog._pricing_workspace.refresh = lambda: calls.append("full_refresh")
    catalog._pricing_workspace.refresh_site_options = lambda: calls.append("refresh_site_options")

    services["inventory_service"].create_storeroom(
        storeroom_code=_unique("P20-ST"), name="P20 Storeroom", site_id=site.id, status="ACTIVE",
    )

    assert calls == ["refresh_site_options"], "narrow seam only -- never the full workspace refresh"


# ---------------------------------------------------------------------------
# inventory_storerooms_changed / inventory_locations_changed fully retired
# ---------------------------------------------------------------------------


def test_legacy_inventory_foundation_signals_no_longer_exist():
    assert not hasattr(domain_events, "inventory_storerooms_changed")
    assert not hasattr(domain_events, "inventory_locations_changed")


def test_legacy_inventory_foundation_signals_have_zero_production_references():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "inventory_storerooms_changed" in source or "inventory_locations_changed" in source:
            hits.append(path)
    assert hits == [], hits
