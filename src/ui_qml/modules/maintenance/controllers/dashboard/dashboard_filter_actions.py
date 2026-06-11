from __future__ import annotations

from .dashboard_property_updates import (
    set_selected_asset_filter,
    set_selected_days_filter,
    set_selected_location_filter,
    set_selected_site_filter,
    set_selected_system_filter,
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


def apply_location_filter(controller, location_id: str) -> None:
    set_selected_location_filter(controller, location_id or "all")
    controller.refresh()


def apply_days_filter(controller, days: int) -> None:
    set_selected_days_filter(controller, str(days))
    controller.refresh()
