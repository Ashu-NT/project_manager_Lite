from __future__ import annotations


def bind_timesheets_domain_events(controller) -> None:
    controller._subscribe_domain_change(
        "timesheet_period",
        "project_tasks",
        "resource",
        scope_code="project_management",
    )


__all__ = ["bind_timesheets_domain_events"]
