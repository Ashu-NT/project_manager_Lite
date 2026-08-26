from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_collaboration_domain_events(controller: object) -> None:
    """P7A: direct-wired to the specific legacy signals this workspace actually reads
    (project/tasks/collaboration/timesheet-period data) -- no generic `domain_changed` bridge."""
    for signal in (
        domain_events.project_changed,
        domain_events.tasks_changed,
        domain_events.collaboration_changed,
        domain_events.timesheet_periods_changed,
    ):
        controller._subscribe_domain_signal(signal, controller._on_domain_event)


__all__ = ["bind_collaboration_domain_events"]
