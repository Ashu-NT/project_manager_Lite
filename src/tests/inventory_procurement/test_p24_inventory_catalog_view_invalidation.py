"""P24: Inventory Item Catalog + Item Category typed events + ViewInvalidation + retirement of
`inventory_items_changed`/`inventory_item_categories_changed`.

Covers: InventoryItemCreated/ProfileUpdated/StatusChanged and
InventoryItemCategoryCreated/ProfileUpdated -> the two proven org-wide read-model targets
(`item_list`, `item_category_list`), the new `InventoryCatalogUnitOfWork` transaction boundary
(Option A convergence for Item + Category sharing one UoW), true no-op semantics, dedupe by
(transaction correlation_id, target identity), the removal of the redundant
`inventory_items_changed` publication from Item document link/unlink (P16D already owns that
projection), the real workspace controllers' narrow/full invalidation wiring, and the full
retirement of both legacy signals (zero producers, zero consumers, fields absent).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.modules.inventory_procurement.application.catalog.event_handlers.view_invalidation import (
    INVENTORY_CATALOG_CATEGORY,
    ITEM_CATEGORY_LIST_SCOPE_CODE,
    ITEM_LIST_SCOPE_CODE,
    build_item_category_list_view_invalidation_handler,
    build_item_list_view_invalidation_handler,
)
from src.core.modules.inventory_procurement.domain.catalog.catalog_events import (
    InventoryItemCategoryCreated,
    InventoryItemCategoryProfileUpdated,
    InventoryItemCreated,
    InventoryItemProfileUpdated,
    InventoryItemStatusChanged,
)
from src.core.platform.common.exceptions import ValidationError
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


def _catalog_hints(hints):
    return [h for h in hints if h.category == INVENTORY_CATALOG_CATEGORY]


# ---------------------------------------------------------------------------
# ViewInvalidation handlers: mapping, dedupe (unit-level, no DB)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event",
    [
        InventoryItemCreated(tenant_id="t1", organization_id="o1", item_id="i1", occurred_at=datetime.now(timezone.utc)),
        InventoryItemProfileUpdated(tenant_id="t1", organization_id="o1", item_id="i1", occurred_at=datetime.now(timezone.utc)),
        InventoryItemStatusChanged(tenant_id="t1", organization_id="o1", item_id="i1", status="ACTIVE", occurred_at=datetime.now(timezone.utc)),
    ],
)
def test_every_item_event_maps_to_item_list_target(event):
    channel = _fake_channel()
    handler = build_item_list_view_invalidation_handler(channel)

    handler(event, _context("tx"))

    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.category == INVENTORY_CATALOG_CATEGORY
    assert hint.scope_code == ITEM_LIST_SCOPE_CODE
    assert isinstance(hint.scope, OrganizationScope)
    assert hint.entity_id == "i1"


@pytest.mark.parametrize(
    "event",
    [
        InventoryItemCategoryCreated(tenant_id="t1", organization_id="o1", category_id="c1", occurred_at=datetime.now(timezone.utc)),
        InventoryItemCategoryProfileUpdated(tenant_id="t1", organization_id="o1", category_id="c1", occurred_at=datetime.now(timezone.utc)),
    ],
)
def test_every_category_event_maps_to_item_category_list_target(event):
    channel = _fake_channel()
    handler = build_item_category_list_view_invalidation_handler(channel)

    handler(event, _context("tx"))

    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.category == INVENTORY_CATALOG_CATEGORY
    assert hint.scope_code == ITEM_CATEGORY_LIST_SCOPE_CODE
    assert isinstance(hint.scope, OrganizationScope)
    assert hint.entity_id == "c1"


def test_item_dedupe_by_org_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_item_list_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(InventoryItemProfileUpdated(tenant_id="t1", organization_id="o1", item_id="i1", occurred_at=now), _context("tx"))
    handler(InventoryItemStatusChanged(tenant_id="t1", organization_id="o1", item_id="i1", status="ACTIVE", occurred_at=now), _context("tx"))
    assert len(channel.notified) == 1, "same org target within one transaction coalesces"

    handler(InventoryItemCreated(tenant_id="t1", organization_id="o2", item_id="i2", occurred_at=now), _context("tx"))
    assert len(channel.notified) == 2, "a different organization within the same transaction is a separate target"

    handler(InventoryItemCreated(tenant_id="t1", organization_id="o1", item_id="i3", occurred_at=now), _context("next-tx"))
    assert len(channel.notified) == 3, "a new transaction is never coalesced with the previous one"


def test_different_organization_hint_is_not_delivered_to_a_scoped_subscription():
    channel = _fake_channel()
    handler = build_item_list_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(InventoryItemCreated(tenant_id="t1", organization_id="o2", item_id="i1", occurred_at=now), _context("tx"))
    hint = channel.notified[0]
    assert ExactOrganization("t1", "o1").matches(hint.scope) is False
    assert ExactOrganization("t1", "o2").matches(hint.scope) is True


# ---------------------------------------------------------------------------
# Real ItemMasterService/ItemCategoryService producer path (InventoryCatalogUnitOfWork)
# ---------------------------------------------------------------------------


def test_create_item_produces_exactly_one_item_list_hint(services):
    hints = _spy_hints(services)

    item = services["inventory_item_service"].create_item(
        item_code=_unique("P24-ITEM"), name="P24 Item", stock_uom="EA",
    )

    catalog_hints = _catalog_hints(hints)
    assert len(catalog_hints) == 1
    assert catalog_hints[0].scope_code == ITEM_LIST_SCOPE_CODE
    assert catalog_hints[0].entity_id == item.id


def test_update_item_true_no_op_produces_zero_hints(services):
    item_service = services["inventory_item_service"]
    item = item_service.create_item(item_code=_unique("P24-ITEM"), name="P24 Item", stock_uom="EA")
    hints = _spy_hints(services)

    unchanged = item_service.update_item(item.id, expected_version=item.version, name="P24 Item")

    assert unchanged.version == item.version, "true no-op: no synthetic version bump"
    assert _catalog_hints(hints) == []


def test_update_item_profile_change_produces_exactly_one_hint(services):
    item_service = services["inventory_item_service"]
    item = item_service.create_item(item_code=_unique("P24-ITEM"), name="P24 Item", stock_uom="EA")
    hints = _spy_hints(services)

    updated = item_service.update_item(item.id, expected_version=item.version, name="P24 Item Renamed")

    assert updated.name == "P24 Item Renamed"
    catalog_hints = _catalog_hints(hints)
    assert len(catalog_hints) == 1
    assert catalog_hints[0].entity_id == item.id


def test_update_item_status_and_profile_change_together_still_coalesce_to_one_hint(services):
    """A single update touching BOTH the profile and the status emits two DIFFERENT typed
    events (ProfileUpdated + StatusChanged) but both map to the SAME `item_list` target -- the
    dedupe layer coalesces them into exactly one ViewInvalidation hint (P24 §21)."""
    item_service = services["inventory_item_service"]
    item = item_service.create_item(
        item_code=_unique("P24-ITEM"), name="P24 Item", stock_uom="EA", status="DRAFT",
    )
    hints = _spy_hints(services)

    updated = item_service.update_item(
        item.id, expected_version=item.version, name="P24 Item Renamed", status="ACTIVE",
    )

    assert updated.status == "ACTIVE"
    catalog_hints = _catalog_hints(hints)
    assert len(catalog_hints) == 1


def test_create_category_produces_exactly_one_item_category_list_hint(services):
    hints = _spy_hints(services)

    category = services["inventory_item_category_service"].create_category(
        category_code=_unique("P24-CAT"), name="P24 Category",
    )

    catalog_hints = _catalog_hints(hints)
    assert len(catalog_hints) == 1
    assert catalog_hints[0].scope_code == ITEM_CATEGORY_LIST_SCOPE_CODE
    assert catalog_hints[0].entity_id == category.id


def test_update_category_true_no_op_produces_zero_hints(services):
    category_service = services["inventory_item_category_service"]
    category = category_service.create_category(category_code=_unique("P24-CAT"), name="P24 Category")
    hints = _spy_hints(services)

    unchanged = category_service.update_category(
        category.id, expected_version=category.version, name="P24 Category",
    )

    assert unchanged.version == category.version, "true no-op: no synthetic version bump"
    assert _catalog_hints(hints) == []


def test_update_category_real_change_produces_exactly_one_hint(services):
    category_service = services["inventory_item_category_service"]
    category = category_service.create_category(category_code=_unique("P24-CAT"), name="P24 Category")
    hints = _spy_hints(services)

    updated = category_service.update_category(
        category.id, expected_version=category.version, is_active=False,
    )

    assert updated.is_active is False
    catalog_hints = _catalog_hints(hints)
    assert len(catalog_hints) == 1
    assert catalog_hints[0].scope_code == ITEM_CATEGORY_LIST_SCOPE_CODE


def test_category_mutation_never_invalidates_item_list(services):
    """§16: Item list rows never embed a cached category label -- proven live at read time in
    `search_items`. A Category fact must never also invalidate `item_list`."""
    hints = _spy_hints(services)

    services["inventory_item_category_service"].create_category(
        category_code=_unique("P24-CAT"), name="P24 Category",
    )

    catalog_hints = _catalog_hints(hints)
    assert all(h.scope_code != ITEM_LIST_SCOPE_CODE for h in catalog_hints)


def test_category_cross_organization_reference_rejected(services):
    """§5: an inactive/nonexistent category code can never be assigned to a new item -- the
    lookup itself is organization-scoped (`_category_repo.get_by_code(organization.id, ...)`),
    so a category from a different organization is indistinguishable from "not found"."""
    with pytest.raises(ValidationError):
        services["inventory_item_service"].create_item(
            item_code=_unique("P24-ITEM"),
            name="P24 Item",
            stock_uom="EA",
            category_code=_unique("NO-SUCH-CATEGORY"),
        )


def test_link_document_produces_zero_item_domain_events_and_zero_item_list_hint(services):
    """§12: document link/unlink never mutates the Item row -- P16D's own `document_links`
    ViewInvalidation is the only expected invalidation; no Item DomainEvent, no `item_list`
    hint."""
    item_service = services["inventory_item_service"]
    item = item_service.create_item(item_code=_unique("P24-ITEM"), name="P24 Item", stock_uom="EA")
    document = services["document_service"].create_document(
        document_code=_unique("P24-DOC"),
        title="P24 Doc",
        document_type="MANUAL",
        storage_kind="REFERENCE",
        storage_uri="vault://p24/doc",
    )
    hints = _spy_hints(services)

    item_service.link_document(item.id, document_id=document.id)

    catalog_hints = _catalog_hints(hints)
    assert catalog_hints == []
    item_service.unlink_document(item.id, document_id=document.id)
    assert _catalog_hints(hints) == []


# ---------------------------------------------------------------------------
# UI: workspace controller narrow/full invalidation wiring
# ---------------------------------------------------------------------------


def test_catalog_workspace_item_list_stale_triggers_full_refresh(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.catalogWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    catalog._catalog_catalog_view_invalidation_adapter.itemListStale.emit("item-1")
    assert refresh_calls == ["refresh"]

    catalog._catalog_catalog_view_invalidation_adapter.itemCategoryListStale.emit("cat-1")
    assert refresh_calls == ["refresh", "refresh"]


def test_pricing_workspace_has_no_catalog_view_invalidation_adapter(services):
    """§20: Pricing has zero source-proven Item/Category dependency -- no adapter instance
    should be constructed for it at all."""
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)

    assert not hasattr(catalog, "_pricing_catalog_view_invalidation_adapter")


@pytest.mark.parametrize(
    "workspace_attr",
    ["inventoryWorkspace", "procurementWorkspace", "reservationsWorkspace"],
)
def test_item_options_consumer_workspaces_narrow_refresh_wiring(services, workspace_attr):
    """§18/§20: Inventory/Procurement/Reservations only need the `item_options` selector, never
    a full workspace refresh, when an Item fact changes."""
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = getattr(catalog, workspace_attr)
    full_refresh_calls = []
    item_option_refresh_calls = []
    controller.refresh = lambda: full_refresh_calls.append("refresh")
    controller.refresh_item_options = lambda: item_option_refresh_calls.append("refresh_item_options")

    adapter_attr = {
        "inventoryWorkspace": "_inventory_catalog_view_invalidation_adapter",
        "procurementWorkspace": "_procurement_catalog_view_invalidation_adapter",
        "reservationsWorkspace": "_reservations_catalog_view_invalidation_adapter",
    }[workspace_attr]
    getattr(catalog, adapter_attr).itemListStale.emit("item-1")

    assert item_option_refresh_calls == ["refresh_item_options"]
    assert full_refresh_calls == []


def test_dashboard_workspace_item_list_stale_triggers_full_refresh(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.dashboardWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    catalog._dashboard_catalog_view_invalidation_adapter.itemListStale.emit("item-1")
    assert refresh_calls == ["refresh"]


# ---------------------------------------------------------------------------
# Legacy signals fully retired
# ---------------------------------------------------------------------------


def test_inventory_items_changed_field_no_longer_exists():
    assert not hasattr(domain_events, "inventory_items_changed")


def test_inventory_item_categories_changed_field_no_longer_exists():
    assert not hasattr(domain_events, "inventory_item_categories_changed")


def test_legacy_catalog_signals_have_zero_production_references():
    """Checks for actual usage (`domain_events.<name>`) or the field declaration, not the bare
    substring -- several UI binder files carry deliberate retirement comments explaining the P24
    removal, which would otherwise false-positive a blanket substring scan (matching this
    session's established convention, e.g. P18B's `resources_changed` retirement comments)."""
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        for needle in (
            "domain_events.inventory_items_changed",
            "inventory_items_changed:",
            "domain_events.inventory_item_categories_changed",
            "inventory_item_categories_changed:",
        ):
            if needle in source:
                hits.append((normalized, needle))
    assert hits == [], hits
