from __future__ import annotations


def bind_scheduling_domain_events(controller: object) -> None:
    controller._subscribe_domain_change(
        "project",
        "project_tasks",
        "project_baseline",
        "resource",
        scope_code="project_management",
    )
    controller._subscribe_domain_change(
        "working_calendar",
        scope_code="platform",
        category="shared_master",
    )


__all__ = ["bind_scheduling_domain_events"]
