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
    selected_entry_id: str | None = None,
    selected_queue_period_id: str | None = None,
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
    review_queue_rows = desktop_api.list_review_queue(status=normalized_queue_status)
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
            review_queue_rows=review_queue_rows,
        ),
        project_options=project_options,
        assignment_options=assignment_options,
        period_options=period_options,
        queue_status_options=queue_status_options,
        selected_project_id=normalized_project_id,
        selected_assignment_id=resolved_assignment_id,
        selected_period_start=resolved_period_start,
        selected_queue_status=normalized_queue_status,
        selected_entry_id=resolved_selected_entry_id,
        selected_queue_period_id=resolved_queue_period_id,
        assignment_summary=build_assignment_summary(snapshot),
        entries=entries_collection,
        selected_entry_detail=build_selected_entry_detail(selected_entry),
        review_queue=review_queue,
        review_detail=build_review_detail(desktop_api, resolved_queue_period_id),
        empty_state=empty_state,
    )
