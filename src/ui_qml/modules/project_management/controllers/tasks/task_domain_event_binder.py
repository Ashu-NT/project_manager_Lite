from __future__ import annotations


def bind_task_domain_events(controller) -> None:
    controller._subscribe_domain_change(
        "project",
        "project_tasks",
        "resource",
        "timesheet_period",
        "task_collaboration",
        scope_code="project_management",
    )


__all__ = ["bind_task_domain_events"]
