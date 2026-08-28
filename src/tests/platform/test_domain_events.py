from src.core.shared.events.domain_events import domain_events
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


# P7A: the generic legacy-compatibility bridge (`_BRIDGE_SPECS`/`_wire_bridges`/`domain_changed`/
# `DomainChangeEvent`/`shared_master_changed`) has been fully removed -- pre-release, no
# compatibility scaffolding kept for it. Every capability's own specific `Signal` field is
# subscribed to directly by its real consumer(s). See `test_p7a_generic_bridge_removal.py` for
# the retirement guards and the direct-wiring proofs.


def test_domain_events_reset_clears_every_signal_without_any_bridge_rewiring():
    """`reset()` no longer calls `_wire_bridges()` (deleted) -- it only clears each Signal's own
    subscriber list. A signal connected before `reset()` must not still be connected after."""
    seen: list[str] = []
    domain_events.documents_changed.connect(lambda doc_id: seen.append(doc_id))

    domain_events.reset()
    domain_events.documents_changed.emit("doc-1")

    assert seen == []
