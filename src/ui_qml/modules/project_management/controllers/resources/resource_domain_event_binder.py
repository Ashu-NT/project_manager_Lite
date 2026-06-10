from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_resource_domain_events(controller) -> None:
    controller._subscribe_domain_change("resource", scope_code="project_management")
    controller._subscribe_domain_change(
        "working_calendar",
        scope_code="platform",
        category="shared_master",
    )
    controller._subscribe_domain_signal(
        domain_events.employees_changed,
        lambda _payload: controller._request_domain_refresh(),
    )


__all__ = ["bind_resource_domain_events"]
