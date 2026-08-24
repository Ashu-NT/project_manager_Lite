from __future__ import annotations

from src.core.shared.events.domain_events import domain_events
from .resource_context_handler import (
    load_resource_activity,
    load_resource_assignments,
    load_resource_projects,
)
from .resource_availability_handler import load_resource_availability


def _reload_if_loaded(controller, section: str) -> None:
    selected = controller._selected_resource_id
    if not selected:
        return
    if section == "projects" and controller._resource_projects_loaded_for:
        load_resource_projects(controller, force=True)
    elif section == "assignments" and controller._resource_assignments_loaded_for:
        load_resource_assignments(controller, force=True)
    elif section == "activity" and controller._resource_activity_loaded_for:
        load_resource_activity(controller, force=True)


def _reload_availability_if_loaded(controller) -> None:
    selected = controller._selected_resource_id
    current = controller._resource_availability or {}
    if not selected or str(current.get("resourceId", "")) != selected:
        return
    start_date = str(current.get("startDate", "") or "")
    end_date = str(current.get("endDate", "") or "")
    if start_date and end_date:
        load_resource_availability(controller, start_date, end_date)


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
    controller._subscribe_domain_signal(
        domain_events.resources_changed,
        lambda resource_id: (
            _reload_if_loaded(controller, "activity")
            if str(resource_id or "") == controller._selected_resource_id
            else None
        ),
    )
    controller._subscribe_domain_signal(
        domain_events.project_changed,
        lambda _project_id: (
            _reload_if_loaded(controller, "projects"),
            _reload_if_loaded(controller, "activity"),
        ),
    )
    controller._subscribe_domain_signal(
        domain_events.tasks_changed,
        lambda _project_id: (
            _reload_if_loaded(controller, "assignments"),
            _reload_availability_if_loaded(controller),
            _reload_if_loaded(controller, "activity"),
        ),
    )
    controller._subscribe_domain_signal(
        domain_events.timesheet_periods_changed,
        lambda _resource_id: _reload_if_loaded(controller, "assignments"),
    )


__all__ = ["bind_resource_domain_events"]
