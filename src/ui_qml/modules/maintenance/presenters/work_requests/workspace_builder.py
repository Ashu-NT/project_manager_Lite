from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestsWorkspaceViewModel,
)

from .detail_builder import build_detail
from .filtering import matches_search, normalize_filter
from .form_options_builder import build_form_options
from .options import option
from .overview_builder import build_overview
from .selection import resolve_selected_id
from .work_request_mapper import work_request_record


def build_empty_state(
    *,
    all_rows,
    filtered_rows,
    search_text: str,
    site_filter: str,
    status_filter: str,
    priority_filter: str,
    asset_filter: str,
) -> str:
    if filtered_rows:
        return ""
    if not all_rows:
        return (
            "No work requests are available yet. "
            "Create a request to start the intake and triage flow."
        )
    if (
        search_text
        or site_filter != "all"
        or status_filter != "all"
        or priority_filter != "all"
        or asset_filter != "all"
    ):
        return "No work requests match the current filters."
    return "No work requests are available yet."


def build_workspace_state(
    desktop_api,
    *,
    search_text: str = "",
    site_filter: str = "all",
    status_filter: str = "all",
    priority_filter: str = "all",
    asset_filter: str = "all",
    selected_work_request_id: str | None = None,
) -> MaintenanceWorkRequestsWorkspaceViewModel:
    site_options = (
        option("all", "All sites"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_sites(active_only=None)
        ),
    )
    status_options = (
        option("all", "All statuses"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_statuses()
        ),
    )
    priority_options = (
        option("all", "All priorities"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_priorities()
        ),
    )

    normalized_site_filter = normalize_filter(site_filter, site_options)
    asset_options = (
        option("all", "All assets"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_asset_options(
                active_only=None,
                site_id=None if normalized_site_filter == "all" else normalized_site_filter,
            )
        ),
    )
    normalized_status_filter = normalize_filter(status_filter, status_options)
    normalized_priority_filter = normalize_filter(priority_filter, priority_options)
    normalized_asset_filter = normalize_filter(asset_filter, asset_options)
    normalized_search = (search_text or "").strip()

    all_rows = desktop_api.list_work_requests()
    filtered_rows = desktop_api.list_work_requests(
        site_id=None if normalized_site_filter == "all" else normalized_site_filter,
        status=None if normalized_status_filter == "all" else normalized_status_filter,
        priority=None if normalized_priority_filter == "all" else normalized_priority_filter,
        asset_id=None if normalized_asset_filter == "all" else normalized_asset_filter,
    )
    if normalized_search:
        filtered_rows = tuple(
            row
            for row in filtered_rows
            if matches_search(
                normalized_search,
                row.work_request_code,
                row.title,
                row.description,
                row.asset_label,
                row.component_label,
                row.system_label,
                row.location_label,
                row.status,
                row.status_label,
                row.priority,
                row.priority_label,
                row.failure_symptom_code,
                row.requested_by_name,
                row.notes,
            )
        )

    resolved_selected_id = resolve_selected_id(selected_work_request_id, filtered_rows)
    selected_row = next(
        (row for row in filtered_rows if row.id == resolved_selected_id),
        None,
    )

    return MaintenanceWorkRequestsWorkspaceViewModel(
        overview=build_overview(all_rows=all_rows, filtered_rows=filtered_rows),
        site_options=site_options,
        status_options=status_options,
        priority_options=priority_options,
        asset_options=asset_options,
        selected_site_filter=normalized_site_filter,
        selected_status_filter=normalized_status_filter,
        selected_priority_filter=normalized_priority_filter,
        selected_asset_filter=normalized_asset_filter,
        search_text=normalized_search,
        work_requests=tuple(work_request_record(row) for row in filtered_rows),
        selected_work_request_id=resolved_selected_id,
        selected_work_request_detail=build_detail(selected_row),
        empty_state=build_empty_state(
            all_rows=all_rows,
            filtered_rows=filtered_rows,
            search_text=normalized_search,
            site_filter=normalized_site_filter,
            status_filter=normalized_status_filter,
            priority_filter=normalized_priority_filter,
            asset_filter=normalized_asset_filter,
        ),
        **build_form_options(desktop_api),
    )
