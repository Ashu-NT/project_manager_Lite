from __future__ import annotations


def on_billing_commercial_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("commercial")


__all__ = ["on_billing_commercial_stale"]
