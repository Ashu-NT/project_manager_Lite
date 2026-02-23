from core.events.domain_events import domain_events


def test_domain_event_signal_connect_emit_disconnect():
    seen: list[str] = []

    def _handler(project_id: str) -> None:
        seen.append(project_id)

    domain_events.project_changed.connect(_handler)
    domain_events.project_changed.emit("p-1")
    domain_events.project_changed.disconnect(_handler)
    domain_events.project_changed.emit("p-2")

    assert seen == ["p-1"]
