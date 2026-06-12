from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_collaboration_domain_events(controller: object) -> None:
    controller._subscribe_domain_change(
        "project",
        "project_tasks",
        "task_collaboration",
        scope_code="project_management",
    )
    controller._subscribe_domain_signal(
        domain_events.approvals_changed,
        controller._on_domain_event,
    )
    controller._subscribe_domain_signal(
        domain_events.timesheet_periods_changed,
        controller._on_domain_event,
    )


__all__ = ["bind_collaboration_domain_events"]
