from __future__ import annotations


def on_project_baseline_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._request_domain_refresh()


__all__ = ["on_project_baseline_stale"]
