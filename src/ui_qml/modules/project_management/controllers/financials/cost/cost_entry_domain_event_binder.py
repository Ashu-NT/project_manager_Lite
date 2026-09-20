from __future__ import annotations


def on_cost_entry_list_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("costs")


def on_cost_entry_actuals_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("overview", "performance", "commercial")


__all__ = ["on_cost_entry_list_stale", "on_cost_entry_actuals_stale"]
