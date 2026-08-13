from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_domain_events(controller) -> None:
    def _on_domain_event(_payload: object) -> None:
        controller._request_domain_refresh()

    for signal in (
        domain_events.organizations_changed,
        domain_events.calendars_changed,
        domain_events.sites_changed,
        domain_events.departments_changed,
        domain_events.employees_changed,
        domain_events.auth_changed,
        domain_events.parties_changed,
        domain_events.documents_changed,
    ):
        controller._subscribe_domain_signal(signal, _on_domain_event)


__all__ = ["bind_domain_events"]
