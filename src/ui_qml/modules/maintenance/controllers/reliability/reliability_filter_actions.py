from __future__ import annotations

from .reliability_property_updates import (
    set_selected_asset_filter,
    set_selected_days_filter,
    set_selected_failure_code_filter,
    set_selected_limit_filter,
    set_selected_location_filter,
    set_selected_site_filter,
    set_selected_system_filter,
    set_selected_threshold_filter,
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


def apply_failure_code_filter(controller, failure_code: str) -> None:
    set_selected_failure_code_filter(controller, failure_code or "all")
    controller.refresh()


def apply_days_filter(controller, days: int) -> None:
    set_selected_days_filter(controller, str(days))
    controller.refresh()


def apply_limit_filter(controller, limit: int) -> None:
    set_selected_limit_filter(controller, str(limit))
    controller.refresh()


def apply_threshold_filter(controller, threshold: int) -> None:
    set_selected_threshold_filter(controller, str(threshold))
    controller.refresh()
