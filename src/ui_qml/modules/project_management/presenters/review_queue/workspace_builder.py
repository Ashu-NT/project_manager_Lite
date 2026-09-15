from __future__ import annotations

from src.core.modules.project_management.api.desktop import ProjectManagementTimesheetsDesktopApi
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetCollectionViewModel,
    TimesheetMetricViewModel,
    TimesheetOverviewViewModel,
    TimesheetSelectorOptionViewModel,
    TimesheetsWorkspaceViewModel,
)

from .filtering import normalize_filter
from .review_builder import build_review_detail
from .review_mapper import to_review_queue_record
from .validation import optional_date


def build_workspace_state(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    *,
    queue_status: str = "SUBMITTED",
    queue_search_text: str = "",
    queue_project_id: str = "all",
    queue_resource_id: str = "all",
    queue_period_start_from: str = "",
    queue_period_start_to: str = "",
    queue_sort_key: str = "submittedAt",
    queue_sort_direction: str = "desc",
    selected_queue_period_id: str | None = None,
    queue_page: int = 1,
    queue_page_size: int = 25,
) -> TimesheetsWorkspaceViewModel:
    project_options = (
        TimesheetSelectorOptionViewModel(value="all", label="All projects"),
        *(
            TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_projects()
        ),
    )
    status_options = tuple(
        TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_queue_statuses()
    )
    normalized_status = normalize_filter(
        queue_status, status_options, default_value="SUBMITTED"
    )
    normalized_project_id = normalize_filter(
        queue_project_id, project_options, default_value="all"
    )
    resource_options = (
        TimesheetSelectorOptionViewModel(value="all", label="All resources"),
        *(
            TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_review_resources(
                project_id=None if normalized_project_id == "all" else normalized_project_id
            )
        ),
    )
    normalized_resource_id = normalize_filter(
        queue_resource_id, resource_options, default_value="all"
    )
    page = desktop_api.list_review_queue_page(
        status=normalized_status,
        search_text=(queue_search_text or "").strip(),
        project_id=None if normalized_project_id == "all" else normalized_project_id,
        resource_id=None if normalized_resource_id == "all" else normalized_resource_id,
        period_start_from=optional_date(queue_period_start_from),
        period_start_to=optional_date(queue_period_start_to),
        page=queue_page,
        page_size=queue_page_size,
        sort_key=queue_sort_key,
        sort_direction=queue_sort_direction,
    )
    visible_ids = {row.period_id for row in page.items}
    requested_id = str(selected_queue_period_id or "").strip()
    selected_id = requested_id if requested_id in visible_ids else ""
    review_queue = TimesheetCollectionViewModel(
        title="Review Queue",
        subtitle="Authoritative TimesheetPeriod decisions in the active scope.",
        empty_state=(
            "No submitted timesheet periods are waiting for review."
            if normalized_status == "SUBMITTED"
            else "No periods match the current queue filter."
        ),
        items=tuple(to_review_queue_record(row) for row in page.items),
    )
    return TimesheetsWorkspaceViewModel(
        overview=TimesheetOverviewViewModel(
            title="Review Queue",
            subtitle="Review submitted timesheet periods with version-safe decisions.",
            metrics=(TimesheetMetricViewModel(
                label="Filtered periods",
                value=str(page.total),
                supporting_text=f"{len(page.items)} on this page",
            ),),
        ),
        project_options=project_options,
        queue_status_options=status_options,
        queue_resource_options=resource_options,
        selected_queue_status=normalized_status,
        queue_search_text=(queue_search_text or "").strip(),
        selected_queue_project_id=normalized_project_id,
        selected_queue_resource_id=normalized_resource_id,
        queue_period_start_from=queue_period_start_from,
        queue_period_start_to=queue_period_start_to,
        queue_sort_key=page.sort_key,
        queue_sort_direction=page.sort_direction,
        selected_queue_period_id=selected_id,
        review_queue=review_queue,
        review_detail=build_review_detail(desktop_api, selected_id),
        empty_state=review_queue.empty_state if not page.items else "",
        queue_total_count=page.total,
        queue_page=page.page,
        queue_page_size=page.page_size,
    )
