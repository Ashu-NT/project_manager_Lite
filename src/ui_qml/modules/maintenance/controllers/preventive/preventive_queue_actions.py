from __future__ import annotations

from .preventive_helpers import normalize_filter, normalize_id


def apply_queue_site_filter(controller, site_id: str) -> None:
    normalized = normalize_filter(site_id)
    if normalized == controller._queue_site_filter:
        return
    controller._queue_site_filter = normalized
    controller._selected_queue_plan_id = ""
    controller._latest_generation_results = []
    controller.refresh()


def apply_queue_due_state_filter(controller, due_state: str) -> None:
    normalized = normalize_filter(due_state)
    if normalized == controller._queue_due_state_filter:
        return
    controller._queue_due_state_filter = normalized
    controller._selected_queue_plan_id = ""
    controller._latest_generation_results = []
    controller.refresh()


def apply_queue_search_text(controller, search_text: str) -> None:
    normalized = normalize_id(search_text)
    if normalized == controller._queue_search_text:
        return
    controller._queue_search_text = normalized
    controller._selected_queue_plan_id = ""
    controller._latest_generation_results = []
    controller.refresh()


def apply_select_queue_plan(controller, plan_id: str) -> None:
    normalized = normalize_id(plan_id)
    if normalized == controller._selected_queue_plan_id:
        return
    controller._selected_queue_plan_id = normalized
    controller._latest_generation_results = []
    controller.refresh()
