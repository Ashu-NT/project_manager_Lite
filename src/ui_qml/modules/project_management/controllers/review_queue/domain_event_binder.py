from __future__ import annotations


def on_task_profile_stale(controller, _project_id: str) -> None:
    """This workspace shows task names/labels on timesheet entries -- only
    name/identity/existence facts (TaskCreated/TaskProfileUpdated/TaskRemoved)
    affect what's displayed, never progress/status/schedule/assignment/
    dependency. No per-project scoping exists on this controller (it is not
    project-scoped), so any project's profile change triggers a refresh --
    narrower than the legacy blanket-every-Task-fact behavior it replaces."""
    controller._request_domain_refresh()


__all__ = ["on_task_profile_stale"]
