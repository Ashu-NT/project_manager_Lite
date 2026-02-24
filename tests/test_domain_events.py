from core.events.domain_events import domain_events
from core.events.signal import Signal


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
