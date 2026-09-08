from src.core.shared.events.domain_events import DomainEvents, domain_events
from src.core.shared.events.signal import Signal


def test_domain_event_signal_connect_emit_disconnect():
    """P46B: `auth_changed` (the last legacy Signal field) is deleted -- `DomainEvents` is now
    intentionally empty (see its own docstring). `Signal` itself remains a legitimate, reused
    generic primitive (see `src/ui_qml/*/controllers/common/workspace_controller_base.py`'s own
    `DomainSignal` alias), so its connect/emit/disconnect mechanics are tested directly here,
    standalone -- not through any `DomainEvents` field."""
    signal: Signal[str] = Signal()
    seen: list[str] = []

    def _handler(user_id: str) -> None:
        seen.append(user_id)

    signal.connect(_handler)
    signal.emit("u-1")
    signal.disconnect(_handler)
    signal.emit("u-2")

    assert seen == ["u-1"]


def test_domain_events_dataclass_is_intentionally_empty():
    """P46B: `auth_changed` was the sole remaining legacy Signal field; `DomainEvents` now
    carries zero fields -- confirmed here directly rather than assumed."""
    import dataclasses

    assert dataclasses.fields(DomainEvents) == ()


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
    subscriber list. `DomainEvents` itself has zero fields now, so this exercises `reset()`
    directly against the shared `domain_events` singleton (a no-op, zero fields to clear) plus a
    standalone `Signal` proving `.clear()` itself (the mechanism `reset()` calls per field) still
    behaves correctly."""
    domain_events.reset()  # zero fields -- must not raise

    signal: Signal[str] = Signal()
    seen: list[str] = []
    signal.connect(lambda user_id: seen.append(user_id))

    signal.clear()
    signal.emit("user-1")

    assert seen == []
