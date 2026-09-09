from __future__ import annotations


def on_budget_planning_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("overview", "planning", "performance")


__all__ = ["on_budget_planning_stale"]
