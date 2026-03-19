from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.notifications.signal import Signal


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


def test_shared_master_changed_bridges_specific_shared_master_events():
    seen: list[DomainChangeEvent] = []

    def _handler(event: DomainChangeEvent) -> None:
        seen.append(event)

    domain_events.shared_master_changed.connect(_handler)
    try:
        domain_events.sites_changed.emit("site-1")
        domain_events.parties_changed.emit("party-1")
    finally:
        domain_events.shared_master_changed.disconnect(_handler)

    assert seen == [
        DomainChangeEvent(
            category="shared_master",
            scope_code="platform",
            entity_type="site",
            entity_id="site-1",
            source_event="sites_changed",
        ),
        DomainChangeEvent(
            category="shared_master",
            scope_code="platform",
            entity_type="party",
            entity_id="party-1",
            source_event="parties_changed",
        ),
    ]


def test_domain_changed_bridges_platform_and_module_events():
    seen: list[DomainChangeEvent] = []

    def _handler(event: DomainChangeEvent) -> None:
        seen.append(event)

    domain_events.domain_changed.connect(_handler)
    try:
        domain_events.project_changed.emit("project-1")
        domain_events.modules_changed.emit("inventory_procurement")
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
        DomainChangeEvent(
            category="platform",
            scope_code="platform",
            entity_type="module_runtime",
            entity_id="inventory_procurement",
            source_event="modules_changed",
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
