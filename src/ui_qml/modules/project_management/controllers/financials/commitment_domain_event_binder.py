from __future__ import annotations


def on_commitment_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations(
            "overview", "planning", "costs", "performance", "commercial"
        )


__all__ = ["on_commitment_stale"]
