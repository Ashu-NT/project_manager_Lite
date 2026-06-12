from __future__ import annotations

from .planner_property_updates import (
    set_search_text_prop,
    set_selected_asset_filter,
    set_selected_request_queue,
    set_selected_site_filter,
    set_selected_system_filter,
    set_selected_work_order_queue,
)


def apply_site_filter(controller, site_id: str) -> None:
    set_selected_site_filter(controller, site_id or "all")
    controller.refresh()


def apply_asset_filter(controller, asset_id: str) -> None:
    set_selected_asset_filter(controller, asset_id or "all")
    controller.refresh()


def apply_system_filter(controller, system_id: str) -> None:
    set_selected_system_filter(controller, system_id or "all")
    controller.refresh()


def apply_request_queue(controller, request_queue: str) -> None:
    set_selected_request_queue(controller, request_queue)
    controller.refresh()


def apply_work_order_queue(controller, work_order_queue: str) -> None:
    set_selected_work_order_queue(controller, work_order_queue)
    controller.refresh()


def apply_search_text(controller, search_text: str) -> None:
    normalized = str(search_text or "").strip()
    if normalized == controller._search_text:
        return
    set_search_text_prop(controller, normalized)
    controller.refresh()
