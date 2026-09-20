from __future__ import annotations


def on_rate_card_list_stale(controller, rate_card_id: str) -> None:
    controller._invalidate_destinations("costs")


def on_rate_card_list_stale_for_project(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._invalidate_destinations("costs")


def on_rate_card_detail_stale(controller, rate_card_id: str) -> None:
    if str(rate_card_id or "") == controller._selected_rate_card_id:
        controller._invalidate_destinations("costs")


__all__ = [
    "on_rate_card_list_stale",
    "on_rate_card_list_stale_for_project",
    "on_rate_card_detail_stale",
]
