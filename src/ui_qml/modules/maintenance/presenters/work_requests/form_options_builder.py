from __future__ import annotations

from .options import option


def build_form_options(desktop_api) -> dict:
    return {
        "form_site_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_sites(active_only=None)
        ),
        "form_location_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_location_options(active_only=None)
        ),
        "form_system_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_system_options(active_only=None)
        ),
        "form_asset_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_asset_options(active_only=None)
        ),
        "form_component_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_component_options(active_only=None)
        ),
        "form_source_type_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_source_types()
        ),
        "form_priority_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_priorities()
        ),
        "form_status_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_statuses()
        ),
    }
