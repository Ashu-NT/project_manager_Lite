"""Composite-controller domain-event subscription for the temporary Admin Console facade.

Why it still exists: `PlatformAdminWorkspaceController` composes 9 single-entity
sub-controllers under one refresh cycle. Since domain events (organization/
calendar/site/department/employee/auth/party/document changes) can originate
from anywhere, the composite subscribes to all of them at once and requests a
single coalesced refresh, rather than each capability subscribing separately.

What contract it preserves: byte-for-byte the same subscription list and
behavior that previously lived in `controllers.admin.admin_domain_event_binder`.

Which later phase removes it: R2, when each capability controller manages its
own domain-event subscriptions independently.
"""

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
