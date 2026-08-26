from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.shared.events.signal import Signal


def test_domain_event_signal_connect_emit_disconnect():
    seen: list[str] = []

    def _handler(project_id: str) -> None:
        seen.append(project_id)

    domain_events.project_changed.connect(_handler)
    domain_events.project_changed.emit("p-1")
    domain_events.project_changed.disconnect(_handler)
    domain_events.project_changed.emit("p-2")

    assert seen == ["p-1"]


def test_signal_emit_prunes_deleted_qt_like_callbacks():
    signal: Signal[str] = Signal()
    seen: list[str] = []

    class _DeletedQtObjectCallback:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, _payload: str) -> None:
            self.calls += 1
            raise RuntimeError("Internal C++ object (PySide6.QtWidgets.QComboBox) already deleted.")

    deleted = _DeletedQtObjectCallback()

    def _ok(payload: str) -> None:
        seen.append(payload)

    signal.connect(deleted)
    signal.connect(_ok)

    signal.emit("p-1")
    signal.emit("p-2")

    assert deleted.calls == 1
    assert seen == ["p-1", "p-2"]


def test_signal_emit_keeps_non_deleted_runtime_errors_visible():
    signal: Signal[str] = Signal()

    def _boom(_payload: str) -> None:
        raise RuntimeError("boom")

    signal.connect(_boom)

    try:
        signal.emit("x")
        assert False, "Expected RuntimeError to propagate"
    except RuntimeError as exc:
        assert str(exc) == "boom"


# P7: `shared_master_changed` retired -- repo-wide audit found zero production consumers (only
# `domain_changed`, via `_subscribe_domain_change(...)`, is ever actually consumed; nothing
# subscribed to this separate, fully-redundant signal). `sites_changed`/`parties_changed` (and
# every other "shared_master"-category bridge entry) still bridge to `domain_changed` exactly as
# before -- see `test_domain_events_reset_rewires_generic_event_bridges` below, which proves this
# for `documents_changed`. See `test_p7_legacy_bridge_removal.py` for the retirement guard.


def test_domain_changed_bridges_module_events():
    """`modules_changed` (the registry's only "platform"-category bridge entry) was retired in
    P5B-3 -- Module Entitlement change notification now flows through the typed DomainEvent ->
    ViewInvalidation -> Qt adapter path instead of this generic legacy bridge."""
    seen: list[DomainChangeEvent] = []

    def _handler(event: DomainChangeEvent) -> None:
        seen.append(event)

    domain_events.domain_changed.connect(_handler)
    try:
        domain_events.project_changed.emit("project-1")
    finally:
        domain_events.domain_changed.disconnect(_handler)

    assert seen == [
        DomainChangeEvent(
            category="module",
            scope_code="project_management",
            entity_type="project",
            entity_id="project-1",
            source_event="project_changed",
        ),
    ]


def test_domain_changed_bridges_inventory_module_events():
    seen: list[DomainChangeEvent] = []

    def _handler(event: DomainChangeEvent) -> None:
        seen.append(event)

    domain_events.domain_changed.connect(_handler)
    try:
        domain_events.inventory_items_changed.emit("item-1")
        domain_events.inventory_storerooms_changed.emit("storeroom-1")
        domain_events.inventory_balances_changed.emit("balance-1")
        domain_events.inventory_reservations_changed.emit("reservation-1")
        domain_events.inventory_locations_changed.emit("location-1")
        domain_events.inventory_reorder_policies_changed.emit("policy-1")
        domain_events.inventory_cycle_counts_changed.emit("cycle-count-1")
    finally:
        domain_events.domain_changed.disconnect(_handler)

    assert seen == [
        DomainChangeEvent(
            category="module",
            scope_code="inventory_procurement",
            entity_type="stock_item",
            entity_id="item-1",
            source_event="inventory_items_changed",
        ),
        DomainChangeEvent(
            category="module",
            scope_code="inventory_procurement",
            entity_type="storeroom",
            entity_id="storeroom-1",
            source_event="inventory_storerooms_changed",
        ),
        DomainChangeEvent(
            category="module",
            scope_code="inventory_procurement",
            entity_type="stock_balance",
            entity_id="balance-1",
            source_event="inventory_balances_changed",
        ),
        DomainChangeEvent(
            category="module",
            scope_code="inventory_procurement",
            entity_type="stock_reservation",
            entity_id="reservation-1",
            source_event="inventory_reservations_changed",
        ),
        DomainChangeEvent(
            category="module",
            scope_code="inventory_procurement",
            entity_type="storage_location",
            entity_id="location-1",
            source_event="inventory_locations_changed",
        ),
        DomainChangeEvent(
            category="module",
            scope_code="inventory_procurement",
            entity_type="reorder_policy",
            entity_id="policy-1",
            source_event="inventory_reorder_policies_changed",
        ),
        DomainChangeEvent(
            category="module",
            scope_code="inventory_procurement",
            entity_type="cycle_count",
            entity_id="cycle-count-1",
            source_event="inventory_cycle_counts_changed",
        ),
    ]


def test_domain_events_reset_rewires_generic_event_bridges():
    seen: list[DomainChangeEvent] = []

    domain_events.reset()

    def _handler(event: DomainChangeEvent) -> None:
        seen.append(event)

    domain_events.domain_changed.connect(_handler)
    try:
        domain_events.documents_changed.emit("doc-1")
    finally:
        domain_events.domain_changed.disconnect(_handler)

    assert seen == [
        DomainChangeEvent(
            category="shared_master",
            scope_code="platform",
            entity_type="document",
            entity_id="doc-1",
            source_event="documents_changed",
        )
    ]

