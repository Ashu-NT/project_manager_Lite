from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetCollectionViewModel,
    TimesheetSelectorOptionViewModel,
    TimesheetsWorkspaceViewModel,
)

from .assignment_builder import build_assignment_summary
from .entry_builder import build_selected_entry_detail
from .entry_mapper import to_entry_record
from .filtering import normalize_filter
from .overview_builder import build_overview
from .review_builder import build_review_detail
from .review_mapper import to_review_queue_record
from .selection import resolve_selected_id
from .validation import optional_date


def build_workspace_state(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    *,
    project_id: str = "all",
    assignment_id: str | None = None,
    period_start: str = "",
    queue_status: str = "SUBMITTED",
    queue_search_text: str = "",
    queue_project_id: str = "all",
    queue_resource_id: str = "all",
    queue_period_start_from: str = "",
    queue_period_start_to: str = "",
    queue_sort_key: str = "submittedAt",
    queue_sort_direction: str = "desc",
    selected_entry_id: str | None = None,
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
    normalized_project_id = normalize_filter(project_id, project_options, default_value="all")
    assignment_options = tuple(
        TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_assignments(
            project_id=None if normalized_project_id == "all" else normalized_project_id
        )
    )
    resolved_assignment_id = resolve_selected_id(assignment_id, assignment_options)
    queue_status_options = tuple(
        TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_queue_statuses()
    )
    normalized_queue_status = normalize_filter(
        queue_status, queue_status_options, default_value="SUBMITTED"
    )
    normalized_queue_project_id = normalize_filter(
        queue_project_id, project_options, default_value="all"
    )
    queue_resource_options = (
        TimesheetSelectorOptionViewModel(value="all", label="All resources"),
        *(
            TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_review_resources(
                project_id=(
                    None
                    if normalized_queue_project_id == "all"
                    else normalized_queue_project_id
                )
            )
        ),
    )
    normalized_queue_resource_id = normalize_filter(
        queue_resource_id, queue_resource_options, default_value="all"
    )
    snapshot = None
    if resolved_assignment_id:
        snapshot = desktop_api.build_assignment_snapshot(
            resolved_assignment_id,
            period_start=optional_date(period_start),
        )
    period_options = tuple(
        TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
        for option in (snapshot.period_options if snapshot is not None else ())
    )
    resolved_period_start = snapshot.selected_period_start if snapshot is not None else ""
    resolved_selected_entry_id = resolve_selected_id(
        selected_entry_id,
        tuple(
            TimesheetSelectorOptionViewModel(value=entry.entry_id, label=entry.entry_date_label)
            for entry in (snapshot.entries if snapshot is not None else ())
        ),
    )
    selected_entry = next(
        (
            entry
            for entry in (snapshot.entries if snapshot is not None else ())
            if entry.entry_id == resolved_selected_entry_id
        ),
        None,
    )
    review_page = desktop_api.list_review_queue_page(
        status=normalized_queue_status,
        search_text=(queue_search_text or "").strip(),
        project_id=(
            None if normalized_queue_project_id == "all" else normalized_queue_project_id
        ),
        resource_id=(
            None if normalized_queue_resource_id == "all" else normalized_queue_resource_id
        ),
        period_start_from=optional_date(queue_period_start_from),
        period_start_to=optional_date(queue_period_start_to),
        page=queue_page,
        page_size=queue_page_size,
        sort_key=queue_sort_key,
        sort_direction=queue_sort_direction,
    )
    review_queue_rows = review_page.items
    review_queue = TimesheetCollectionViewModel(
        title="Review Queue",
        subtitle="Submitted or locked periods waiting for review or follow-up.",
        empty_state=(
            "No periods match the current queue filter."
            if normalized_queue_status != "SUBMITTED"
            else "No submitted timesheet periods are waiting for review."
        ),
        items=tuple(to_review_queue_record(row) for row in review_queue_rows),
    )
    resolved_queue_period_id = resolve_selected_id(
        selected_queue_period_id,
        tuple(
            TimesheetSelectorOptionViewModel(value=row.period_id, label=row.resource_name)
            for row in review_queue_rows
        ),
    )
    entries_collection = TimesheetCollectionViewModel(
        title="Time Entries",
        subtitle="Period entries for the selected task assignment.",
        empty_state=(
            "Select a task assignment to review or capture labor entries."
            if snapshot is None
            else "No time entries are available yet for the selected period."
        ),
        items=tuple(
            to_entry_record(entry)
            for entry in (snapshot.entries if snapshot is not None else ())
        ),
    )
    empty_state = (
        ""
        if snapshot is not None or review_queue_rows
        else "No timesheet assignments or review periods are available in the current scope."
    )
    return TimesheetsWorkspaceViewModel(
        overview=build_overview(
            assignment_options=assignment_options,
            snapshot=snapshot,
            review_queue_total=review_page.total,
        ),
        project_options=project_options,
        assignment_options=assignment_options,
        period_options=period_options,
        queue_status_options=queue_status_options,
        queue_resource_options=queue_resource_options,
        selected_project_id=normalized_project_id,
        selected_assignment_id=resolved_assignment_id,
        selected_period_start=resolved_period_start,
        selected_queue_status=normalized_queue_status,
        queue_search_text=(queue_search_text or "").strip(),
        selected_queue_project_id=normalized_queue_project_id,
        selected_queue_resource_id=normalized_queue_resource_id,
        queue_period_start_from=queue_period_start_from,
        queue_period_start_to=queue_period_start_to,
        queue_sort_key=review_page.sort_key,
        queue_sort_direction=review_page.sort_direction,
        selected_entry_id=resolved_selected_entry_id,
        selected_queue_period_id=resolved_queue_period_id,
        assignment_summary=build_assignment_summary(snapshot),
        entries=entries_collection,
        selected_entry_detail=build_selected_entry_detail(selected_entry),
        review_queue=review_queue,
        review_detail=build_review_detail(desktop_api, resolved_queue_period_id),
        empty_state=empty_state,
        queue_total_count=review_page.total,
        queue_page=review_page.page,
        queue_page_size=review_page.page_size,
    )
