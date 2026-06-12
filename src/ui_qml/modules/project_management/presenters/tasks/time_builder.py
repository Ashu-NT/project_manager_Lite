from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskSelectorOptionViewModel,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetCollectionViewModel,
    TimesheetDetailFieldViewModel,
    TimesheetDetailViewModel,
)

from .assignment_mapper import build_time_assignment_options
from .overview_builder import build_empty_overview
from .selection import resolve_assignment_id, resolve_time_entry_id
from .time_mapper import to_time_entry_record_view_model
from .validation import optional_iso_date


def build_time_assignment_summary(snapshot) -> TimesheetDetailViewModel:
    if snapshot is None:
        return TimesheetDetailViewModel(
            title="No assignment selected",
            empty_state=(
                "Select a task assignment to review detailed time entries, "
                "period status, and labor totals."
            ),
        )
    summary = snapshot.period_summary
    return TimesheetDetailViewModel(
        id=snapshot.assignment.value,
        title=snapshot.assignment.label,
        status_label=summary.status_label,
        subtitle=f"{summary.period_start_label} -> {summary.period_end_label}",
        description=snapshot.scope_summary,
        fields=(
            TimesheetDetailFieldViewModel(
                label="Resource",
                value=summary.resource_name,
            ),
            TimesheetDetailFieldViewModel(
                label="Hours",
                value=summary.total_hours_label,
                supporting_text=(
                    f"{summary.entry_count} entry or entries in the selected resource month."
                ),
            ),
            TimesheetDetailFieldViewModel(
                label="Submitted by",
                value=summary.submitted_by_username,
                supporting_text=summary.submitted_at_label,
            ),
            TimesheetDetailFieldViewModel(
                label="Decision",
                value=summary.decided_by_username,
                supporting_text=summary.decided_at_label,
            ),
            TimesheetDetailFieldViewModel(
                label="Decision note",
                value=summary.decision_note or "No review note recorded.",
            ),
        ),
        state={
            "assignmentId": snapshot.assignment.value,
            "resourceId": summary.resource_id,
            "periodStart": snapshot.selected_period_start,
            "periodId": summary.period_id,
            "projectId": snapshot.assignment.project_id,
        },
    )


def build_time_entries_collection(snapshot) -> TimesheetCollectionViewModel:
    if snapshot is None:
        return TimesheetCollectionViewModel(
            title="Time Entries",
            subtitle="Detailed labor entries for the selected task assignment.",
            empty_state="Select a task assignment to review or capture labor entries.",
        )
    return TimesheetCollectionViewModel(
        title="Time Entries",
        subtitle="Detailed labor entries for the selected task assignment.",
        empty_state="No time entries are available yet for the selected period.",
        items=tuple(
            to_time_entry_record_view_model(entry)
            for entry in snapshot.entries
        ),
    )


def build_selected_time_entry_detail(selected_entry) -> TimesheetDetailViewModel:
    if selected_entry is None:
        return TimesheetDetailViewModel(
            title="No entry selected",
            empty_state=(
                "Select an entry from the period list to review or edit "
                "its captured labor note."
            ),
        )
    return TimesheetDetailViewModel(
        id=selected_entry.entry_id,
        title=selected_entry.entry_date_label,
        status_label=selected_entry.hours_label,
        subtitle=selected_entry.author_username,
        description=selected_entry.note or "No labor note recorded.",
        fields=(
            TimesheetDetailFieldViewModel(
                label="Date", value=selected_entry.entry_date_label
            ),
            TimesheetDetailFieldViewModel(
                label="Hours", value=selected_entry.hours_label
            ),
            TimesheetDetailFieldViewModel(
                label="Author", value=selected_entry.author_username
            ),
        ),
        state={
            "entryId": selected_entry.entry_id,
            "entryDate": selected_entry.entry_date_label,
            "hours": str(selected_entry.hours),
            "note": selected_entry.note,
        },
    )


def build_task_time_state(
    desktop_api,
    timesheets_desktop_api,
    *,
    task_id: str,
    selected_assignment_id: str | None = None,
    selected_time_period_start: str = "",
    selected_time_entry_id: str | None = None,
) -> TaskCatalogWorkspaceViewModel:
    normalized_task_id = (task_id or "").strip()
    assignments = tuple(
        desktop_api.list_assignments(normalized_task_id)
        if normalized_task_id
        else ()
    )
    assignment_options = build_time_assignment_options(assignments)
    resolved_assignment_id = resolve_assignment_id(selected_assignment_id, assignments)

    timesheet_snapshot = (
        timesheets_desktop_api.build_assignment_snapshot(
            resolved_assignment_id,
            period_start=optional_iso_date(selected_time_period_start),
        )
        if resolved_assignment_id
        else None
    )

    time_period_options = tuple(
        TaskSelectorOptionViewModel(value=option.value, label=option.label)
        for option in (
            timesheet_snapshot.period_options
            if timesheet_snapshot is not None
            else ()
        )
    )
    resolved_time_period_start = (
        timesheet_snapshot.selected_period_start
        if timesheet_snapshot is not None
        else ""
    )
    resolved_time_entry_id = resolve_time_entry_id(
        selected_time_entry_id,
        timesheet_snapshot.entries if timesheet_snapshot is not None else (),
    )
    selected_time_entry = next(
        (
            entry
            for entry in (
                timesheet_snapshot.entries if timesheet_snapshot is not None else ()
            )
            if entry.entry_id == resolved_time_entry_id
        ),
        None,
    )
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_task_id=normalized_task_id,
        assignment_options=assignment_options,
        selected_assignment_id=resolved_assignment_id,
        time_period_options=time_period_options,
        selected_time_period_start=resolved_time_period_start,
        time_assignment_summary=build_time_assignment_summary(timesheet_snapshot),
        time_entries=build_time_entries_collection(timesheet_snapshot),
        selected_time_entry_id=resolved_time_entry_id,
        selected_time_entry_detail=build_selected_time_entry_detail(selected_time_entry),
    )


def build_empty_task_time_state() -> TaskCatalogWorkspaceViewModel:
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_assignment_id="",
        selected_time_period_start="",
        selected_time_entry_id="",
        time_period_options=(),
        time_assignment_summary=build_time_assignment_summary(None),
        time_entries=build_time_entries_collection(None),
        selected_time_entry_detail=build_selected_time_entry_detail(None),
    )


def build_task_time_entries_refresh(
    timesheets_desktop_api,
    *,
    assignment_id: str | None,
    period_start: str = "",
    selected_time_entry_id: str | None = None,
) -> TaskCatalogWorkspaceViewModel | None:
    if not assignment_id:
        return None
    try:
        timesheet_snapshot = timesheets_desktop_api.build_assignment_snapshot(
            assignment_id,
            period_start=optional_iso_date(period_start),
        )
    except Exception:
        return None
    resolved_time_entry_id = resolve_time_entry_id(
        selected_time_entry_id,
        timesheet_snapshot.entries,
    )
    selected_time_entry = next(
        (e for e in timesheet_snapshot.entries if e.entry_id == resolved_time_entry_id),
        None,
    )
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_assignment_id=assignment_id,
        selected_time_period_start=timesheet_snapshot.selected_period_start or period_start,
        selected_time_entry_id=resolved_time_entry_id or "",
        time_period_options=(),
        time_assignment_summary=build_time_assignment_summary(timesheet_snapshot),
        time_entries=build_time_entries_collection(timesheet_snapshot),
        selected_time_entry_detail=build_selected_time_entry_detail(selected_time_entry),
    )
