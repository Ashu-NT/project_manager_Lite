from __future__ import annotations

from .options import SOURCE_TYPE_OPTIONS, option


def build_form_options(desktop_api, *, site_id: str | None) -> dict:
    return {
        "form_site_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_sites(active_only=None)
        ),
        "form_location_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_location_options(active_only=None, site_id=site_id)
        ),
        "form_system_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_system_options(active_only=None, site_id=site_id)
        ),
        "form_asset_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_asset_options(active_only=None, site_id=site_id)
        ),
        "form_component_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_component_options(active_only=None)
        ),
        "form_source_type_options": SOURCE_TYPE_OPTIONS,
        "form_source_work_request_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_source_work_request_options(site_id=site_id)
        ),
        "form_work_order_type_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_work_order_types()
        ),
        "form_priority_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_priorities()
        ),
        "form_status_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_statuses()
        ),
        "form_employee_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_employee_options(active_only=None, site_id=site_id)
        ),
        "form_vendor_options": tuple(
            option(opt.value, opt.label)
            for opt in desktop_api.list_vendor_parties(active_only=None)
        ),
    }
