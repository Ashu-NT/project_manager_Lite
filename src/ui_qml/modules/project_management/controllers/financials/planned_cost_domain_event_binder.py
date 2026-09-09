from __future__ import annotations


def on_planned_cost_snapshot_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("planning", "performance")


__all__ = ["on_planned_cost_snapshot_stale"]
