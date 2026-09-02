from __future__ import annotations


def on_financial_profile_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("controls")


__all__ = ["on_financial_profile_stale"]
