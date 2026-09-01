from __future__ import annotations


def on_forecast_planning_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("planning")


def on_forecast_approved_basis_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("overview", "planning", "performance", "commercial")


__all__ = ["on_forecast_planning_stale", "on_forecast_approved_basis_stale"]
