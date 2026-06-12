from __future__ import annotations

from .work_orders_helpers import normalize_filter, normalize_id
from .work_orders_property_updates import (
    set_search_text_prop,
    set_selected_asset_filter,
    set_selected_priority_filter,
    set_selected_site_filter,
    set_selected_status_filter,
    set_selected_work_order_id,
    set_selected_work_order_type_filter,
)


def apply_search_text(controller, search_text: str) -> None:
    normalized = normalize_id(search_text)
    if normalized == controller._search_text:
        return
    set_search_text_prop(controller, normalized)
    controller.refresh()


def apply_site_filter(controller, site_id: str) -> None:
    normalized = normalize_filter(site_id)
    if normalized == controller._selected_site_filter:
        return
    set_selected_site_filter(controller, normalized)
    controller.refresh()


def apply_status_filter(controller, status: str) -> None:
    normalized = normalize_filter(status)
    if normalized == controller._selected_status_filter:
        return
    set_selected_status_filter(controller, normalized)
    controller.refresh()


def apply_priority_filter(controller, priority: str) -> None:
    normalized = normalize_filter(priority)
    if normalized == controller._selected_priority_filter:
        return
    set_selected_priority_filter(controller, normalized)
    controller.refresh()


def apply_work_order_type_filter(controller, work_order_type: str) -> None:
    normalized = normalize_filter(work_order_type)
    if normalized == controller._selected_work_order_type_filter:
        return
    set_selected_work_order_type_filter(controller, normalized)
    controller.refresh()


def apply_asset_filter(controller, asset_id: str) -> None:
    normalized = normalize_filter(asset_id)
    if normalized == controller._selected_asset_filter:
        return
    set_selected_asset_filter(controller, normalized)
    controller.refresh()


def apply_select_work_order(controller, work_order_id: str) -> None:
    normalized = normalize_id(work_order_id)
    if normalized == controller._selected_work_order_id:
        return
    set_selected_work_order_id(controller, normalized)
    controller.refresh()
