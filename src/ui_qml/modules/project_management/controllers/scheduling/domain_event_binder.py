from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_scheduling_domain_events(controller: object) -> None:
    """P7A: direct-wired to the specific legacy signals this workspace actually reads -- no
    generic `domain_changed` bridge."""

    def _on_domain_event(_payload: object) -> None:
        controller._request_domain_refresh()

    for signal in (
        domain_events.project_changed,
        domain_events.tasks_changed,
        domain_events.baseline_changed,
        domain_events.resources_changed,
        domain_events.calendars_changed,
    ):
        controller._subscribe_domain_signal(signal, _on_domain_event)


__all__ = ["bind_scheduling_domain_events"]
