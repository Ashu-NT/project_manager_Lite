from __future__ import annotations


def _selected(controller, project_id: str) -> bool:
    return str(project_id or "") == controller._selected_project_id


def on_financial_change_workspace_stale(controller, project_id: str) -> None:
    if _selected(controller, project_id):
        controller._invalidate_destinations("controls")


def on_financial_change_budget_stale(controller, project_id: str) -> None:
    if _selected(controller, project_id):
        controller._invalidate_destinations("controls", "overview", "performance")


def on_financial_change_forecast_stale(controller, project_id: str) -> None:
    if _selected(controller, project_id):
        controller._invalidate_destinations(
            "controls", "planning", "overview", "performance", "commercial"
        )


def on_financial_change_schedule_stale(controller, project_id: str) -> None:
    if _selected(controller, project_id):
        controller._invalidate_destinations(
            "controls", "planning", "overview", "performance"
        )


__all__ = [
    "on_financial_change_budget_stale",
    "on_financial_change_forecast_stale",
    "on_financial_change_schedule_stale",
    "on_financial_change_workspace_stale",
]
