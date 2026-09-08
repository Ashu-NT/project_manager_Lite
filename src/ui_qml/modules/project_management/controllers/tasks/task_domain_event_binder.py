from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_task_domain_events(controller) -> None:

    def _on_domain_event(_payload: object) -> None:
        controller._request_domain_refresh()

    for signal in (
        domain_events.tasks_changed,
    ):
        controller._subscribe_domain_signal(signal, _on_domain_event)


def on_timesheet_project_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._request_domain_refresh()


__all__ = ["bind_task_domain_events", "on_timesheet_project_stale"]
