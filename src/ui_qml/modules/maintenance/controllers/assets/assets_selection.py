from __future__ import annotations

from .assets_helpers import normalize_filter, normalize_id
from .assets_property_updates import (
    set_search_text_prop,
    set_selected_active_filter,
    set_selected_asset_id,
    set_selected_component_id,
    set_selected_location_id,
    set_selected_site_filter,
    set_selected_system_id,
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


def apply_active_filter(controller, active_filter: str) -> None:
    normalized = normalize_filter(active_filter)
    if normalized == controller._selected_active_filter:
        return
    set_selected_active_filter(controller, normalized)
    controller.refresh()


def apply_select_location(controller, location_id: str) -> None:
    normalized = normalize_id(location_id)
    if normalized == controller._selected_location_id:
        return
    set_selected_location_id(controller, normalized)
    controller.refresh()


def apply_select_system(controller, system_id: str) -> None:
    normalized = normalize_id(system_id)
    if normalized == controller._selected_system_id:
        return
    set_selected_system_id(controller, normalized)
    controller.refresh()


def apply_select_asset(controller, asset_id: str) -> None:
    normalized = normalize_id(asset_id)
    if normalized == controller._selected_asset_id:
        return
    set_selected_asset_id(controller, normalized)
    controller.refresh()


def apply_select_component(controller, component_id: str) -> None:
    normalized = normalize_id(component_id)
    if normalized == controller._selected_component_id:
        return
    set_selected_component_id(controller, normalized)
    controller.refresh()
