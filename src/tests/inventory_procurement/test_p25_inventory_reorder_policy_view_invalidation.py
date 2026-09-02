"""P25: Inventory Reorder Policy typed event + ViewInvalidation + retirement of
`inventory_reorder_policies_changed`.

Covers: `InventoryReorderPolicyConfigured` (one semantic event for the single
`upsert_reorder_policy` business operation -- the caller never distinguishes create vs. update,
so this is not split into Created/Updated) -> the single proven org-wide read-model target
(`reorder_policy_list`), the `reorder_policies` accessor added to the EXISTING
`InventoryFoundationUnitOfWork` (Option A convergence, shared with Storeroom/Location), true
no-op semantics on the update-via-scope-lookup path, dedupe by (transaction correlation_id,
target identity), the real Inventory workspace's full-refresh wiring (no narrower seam exists in
its own monolithic `build_workspace_state`), and the full retirement of
`inventory_reorder_policies_changed` (zero producers, zero consumers, field absent).
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.inventory_procurement.application.inventory.event_handlers.view_invalidation import (
    INVENTORY_CATEGORY,
    REORDER_POLICY_LIST_SCOPE_CODE,
    build_reorder_policy_list_view_invalidation_handler,
)
from src.core.modules.inventory_procurement.domain.inventory.foundation_events import (
    InventoryReorderPolicyConfigured,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import ExactOrganization, OrganizationScope

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _context(correlation_id: str) -> DomainEventContext:
    return DomainEventContext(correlation_id=correlation_id)


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _reorder_policy_hints(hints):
    return [h for h in hints if h.category == INVENTORY_CATEGORY and h.scope_code == REORDER_POLICY_LIST_SCOPE_CODE]


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _seed_item_and_storeroom(services):
    from src.core.platform.domain.master_data.party import PartyType

    site = services["site_service"].create_site(
        site_code=_unique("P25-SITE"), name="P25 Site", currency_code="USD",
    )
    supplier = services["party_service"].create_party(
        party_code=_unique("P25-SUP"), party_name="P25 Supplier", party_type=PartyType.SUPPLIER,
    )
    item = services["inventory_item_service"].create_item(
        item_code=_unique("P25-ITEM"), name="P25 Item", stock_uom="EA", preferred_party_id=supplier.id,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique("P25-ST"), name="P25 Storeroom", site_id=site.id, storeroom_type="MAIN",
    )
    return item, storeroom, supplier


# ---------------------------------------------------------------------------
# ViewInvalidation handler: mapping, dedupe (unit-level, no DB)
# ---------------------------------------------------------------------------


def test_configured_event_maps_to_reorder_policy_list_target():
    channel = _fake_channel()
    handler = build_reorder_policy_list_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        InventoryReorderPolicyConfigured(
            tenant_id="t1", organization_id="o1", policy_id="p1",
            stock_item_id="i1", storeroom_id="s1", location_id=None, occurred_at=now,
        ),
        _context("tx"),
    )

    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.category == INVENTORY_CATEGORY
    assert hint.scope_code == REORDER_POLICY_LIST_SCOPE_CODE
    assert isinstance(hint.scope, OrganizationScope)
    assert hint.entity_id == "p1"


def test_dedupe_by_org_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_reorder_policy_list_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        InventoryReorderPolicyConfigured(
            tenant_id="t1", organization_id="o1", policy_id="p1",
            stock_item_id="i1", storeroom_id="s1", location_id=None, occurred_at=now,
        ),
        _context("tx"),
    )
    handler(
        InventoryReorderPolicyConfigured(
            tenant_id="t1", organization_id="o1", policy_id="p2",
            stock_item_id="i2", storeroom_id="s1", location_id=None, occurred_at=now,
        ),
        _context("tx"),
    )
    assert len(channel.notified) == 1, "same org target within one transaction coalesces"

    handler(
        InventoryReorderPolicyConfigured(
            tenant_id="t1", organization_id="o2", policy_id="p3",
            stock_item_id="i3", storeroom_id="s2", location_id=None, occurred_at=now,
        ),
        _context("tx"),
    )
    assert len(channel.notified) == 2, "a different organization within the same transaction is a separate target"

    handler(
        InventoryReorderPolicyConfigured(
            tenant_id="t1", organization_id="o1", policy_id="p4",
            stock_item_id="i4", storeroom_id="s1", location_id=None, occurred_at=now,
        ),
        _context("next-tx"),
    )
    assert len(channel.notified) == 3, "a new transaction is never coalesced with the previous one"


def test_different_organization_hint_is_not_delivered_to_a_scoped_subscription():
    channel = _fake_channel()
    handler = build_reorder_policy_list_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        InventoryReorderPolicyConfigured(
            tenant_id="t1", organization_id="o2", policy_id="p1",
            stock_item_id="i1", storeroom_id="s1", location_id=None, occurred_at=now,
        ),
        _context("tx"),
    )
    hint = channel.notified[0]
    assert ExactOrganization("t1", "o1").matches(hint.scope) is False
    assert ExactOrganization("t1", "o2").matches(hint.scope) is True


# ---------------------------------------------------------------------------
# Real InventoryFoundationService producer path (InventoryFoundationUnitOfWork)
# ---------------------------------------------------------------------------


def test_create_via_upsert_produces_exactly_one_hint(services):
    _login(services, "admin", "ChangeMe123!")
    item, storeroom, supplier = _seed_item_and_storeroom(services)
    hints = _spy_hints(services)

    policy = services["inventory_foundation_service"].upsert_reorder_policy(
        stock_item_id=item.id, storeroom_id=storeroom.id,
        min_qty=2, max_qty=12, reorder_point=4, reorder_qty=6,
        preferred_supplier_party_id=supplier.id,
    )

    policy_hints = _reorder_policy_hints(hints)
    assert len(policy_hints) == 1
    assert policy_hints[0].entity_id == policy.id


def test_update_via_scope_lookup_produces_exactly_one_hint(services):
    _login(services, "admin", "ChangeMe123!")
    item, storeroom, supplier = _seed_item_and_storeroom(services)
    foundation_service = services["inventory_foundation_service"]
    foundation_service.upsert_reorder_policy(
        stock_item_id=item.id, storeroom_id=storeroom.id,
        min_qty=2, max_qty=12, reorder_point=4, reorder_qty=6,
    )
    hints = _spy_hints(services)

    updated = foundation_service.upsert_reorder_policy(
        stock_item_id=item.id, storeroom_id=storeroom.id,
        min_qty=2, max_qty=12, reorder_point=5, reorder_qty=6,
    )

    assert updated.reorder_point == 5
    policy_hints = _reorder_policy_hints(hints)
    assert len(policy_hints) == 1


def test_update_true_no_op_produces_zero_hints(services):
    _login(services, "admin", "ChangeMe123!")
    item, storeroom, supplier = _seed_item_and_storeroom(services)
    foundation_service = services["inventory_foundation_service"]
    policy = foundation_service.upsert_reorder_policy(
        stock_item_id=item.id, storeroom_id=storeroom.id,
        min_qty=2, max_qty=12, reorder_point=4, reorder_qty=6,
    )
    hints = _spy_hints(services)

    unchanged = foundation_service.upsert_reorder_policy(
        stock_item_id=item.id, storeroom_id=storeroom.id,
        min_qty=2, max_qty=12, reorder_point=4, reorder_qty=6,
    )

    assert unchanged.version == policy.version, "true no-op: no synthetic version bump"
    assert _reorder_policy_hints(hints) == []


def test_update_via_explicit_policy_id_produces_exactly_one_hint(services):
    _login(services, "admin", "ChangeMe123!")
    item, storeroom, supplier = _seed_item_and_storeroom(services)
    foundation_service = services["inventory_foundation_service"]
    policy = foundation_service.upsert_reorder_policy(
        stock_item_id=item.id, storeroom_id=storeroom.id,
        min_qty=2, max_qty=12, reorder_point=4, reorder_qty=6,
    )
    hints = _spy_hints(services)

    updated = foundation_service.upsert_reorder_policy(
        stock_item_id=item.id, storeroom_id=storeroom.id,
        policy_id=policy.id, expected_version=policy.version,
        min_qty=2, max_qty=12, reorder_point=4, reorder_qty=9,
    )

    assert updated.reorder_qty == 9
    policy_hints = _reorder_policy_hints(hints)
    assert len(policy_hints) == 1
    assert policy_hints[0].entity_id == policy.id


# ---------------------------------------------------------------------------
# UI: Inventory workspace full-refresh wiring
# ---------------------------------------------------------------------------


def test_inventory_workspace_reorder_policy_list_stale_triggers_full_refresh(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.inventoryWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    catalog._inventory_foundation_view_invalidation_adapter.reorderPolicyListStale.emit("policy-1")
    assert refresh_calls == ["refresh"]


# ---------------------------------------------------------------------------
# Legacy signal fully retired
# ---------------------------------------------------------------------------


def test_inventory_reorder_policies_changed_field_no_longer_exists():
    assert not hasattr(domain_events, "inventory_reorder_policies_changed")


def test_inventory_reorder_policies_changed_has_zero_production_references():
    """Checks for actual usage (`domain_events.inventory_reorder_policies_changed`) or the field
    declaration, not the bare substring -- several UI binder files carry deliberate retirement
    comments explaining the P25 removal, which would otherwise false-positive a blanket
    substring scan (matching this session's established convention)."""
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if (
            "domain_events.inventory_reorder_policies_changed" in source
            or "inventory_reorder_policies_changed:" in source
        ):
            hits.append(normalized)
    assert hits == [], hits
