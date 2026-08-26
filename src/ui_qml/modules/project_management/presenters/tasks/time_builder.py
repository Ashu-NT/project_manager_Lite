from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskSelectorOptionViewModel,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetDetailFieldViewModel,
    TimesheetDetailViewModel,
)

from .assignment_mapper import build_time_assignment_options
from .overview_builder import build_empty_overview
from .selection import resolve_time_entry_id


def build_task_time_summary_dict(summary_dto) -> dict[str, object] | None:
    """Task-scoped (never resource-wide) planned/actual/remaining/overrun
    totals plus the per-resource breakdown, straight from
    TaskTimeSummaryDesktopDto (docs §44 Time redesign) -- rendered as-is,
    never recalculated in QML."""
    if summary_dto is None:
        return None
    return {
        "hasSummary": True,
        "taskId": summary_dto.task_id,
        "plannedHoursLabel": summary_dto.planned_hours_label,
        "actualHoursLabel": summary_dto.actual_hours_label,
        "remainingHoursLabel": summary_dto.remaining_hours_label,
        "overrunHoursLabel": summary_dto.overrun_hours_label,
        "hasOverrun": summary_dto.has_overrun,
        "burnStatus": summary_dto.burn_status,
        "burnStatusLabel": summary_dto.burn_status_label,
        "assignmentCount": summary_dto.assignment_count,
        "resourceBreakdown": [
            {
                "assignmentId": row.assignment_id,
                "resourceId": row.resource_id,
                "resourceName": row.resource_name,
                "plannedHoursLabel": row.planned_hours_label,
                "actualHoursLabel": row.actual_hours_label,
                "remainingHoursLabel": row.remaining_hours_label,
                "overrunHoursLabel": row.overrun_hours_label,
                "hasOverrun": row.has_overrun,
                "burnStatus": row.burn_status,
                "burnStatusLabel": row.burn_status_label,
            }
            for row in summary_dto.resource_breakdown
        ],
    }


def build_task_time_entries_page_dict(page_dto) -> dict[str, object] | None:
    """Task-scoped (every assignment on this task), all-time Time Entries
    page straight from TaskTimeEntriesPageDesktopDto (docs §44 Time
    redesign) -- authoritative paging, not a locally-filtered slice of a
    truncated dataset."""
    if page_dto is None:
        return None
    return {
        "items": [
            {
                "id": item.entry_id,
                "entryId": item.entry_id,
                "assignmentId": item.assignment_id,
                "resourceId": item.resource_id,
                "resourceName": item.resource_name,
                "entryDateLabel": item.entry_date_label,
                "hours": item.hours,
                "hoursLabel": item.hours_label,
                "note": item.note,
                "authorUsername": item.author_username,
                "version": item.version,
            }
            for item in page_dto.items
        ],
        "total": page_dto.total,
        "page": page_dto.page,
        "pageSize": page_dto.page_size,
    }


def build_selected_time_entry_detail(entry_dto) -> TimesheetDetailViewModel:
    if entry_dto is None:
        return TimesheetDetailViewModel(
            title="No entry selected",
            empty_state=(
                "Select an entry from Time Entries to review or edit its "
                "captured note."
            ),
        )
    return TimesheetDetailViewModel(
        id=entry_dto.entry_id,
        title=entry_dto.entry_date_label,
        status_label=entry_dto.hours_label,
        subtitle=entry_dto.resource_name,
        description=entry_dto.note or "No description recorded.",
        fields=(
            TimesheetDetailFieldViewModel(label="Date", value=entry_dto.entry_date_label),
            TimesheetDetailFieldViewModel(label="Resource", value=entry_dto.resource_name),
            TimesheetDetailFieldViewModel(label="Hours", value=entry_dto.hours_label),
            TimesheetDetailFieldViewModel(
                label="Recorded by", value=entry_dto.author_username or "unknown"
            ),
        ),
        state={
            "entryId": entry_dto.entry_id,
            "assignmentId": entry_dto.assignment_id,
            "entryDate": entry_dto.entry_date_label,
            "hours": str(entry_dto.hours),
            "note": entry_dto.note,
            "authorUsername": entry_dto.author_username or "",
            "version": entry_dto.version,
        },
    )


def build_task_time_state(
    desktop_api,
    timesheets_desktop_api,
    *,
    task_id: str,
    resource_filter: str = "",
    page: int = 1,
    page_size: int = 25,
    selected_time_entry_id: str | None = None,
) -> TaskCatalogWorkspaceViewModel:
    normalized_task_id = (task_id or "").strip()
    assignments = tuple(
        desktop_api.list_assignments(normalized_task_id) if normalized_task_id else ()
    )
    assignment_options = build_time_assignment_options(assignments)

    summary_dto = (
        desktop_api.get_task_time_summary(normalized_task_id)
        if normalized_task_id
        else None
    )
    entries_page_dto = (
        desktop_api.list_task_time_entries(
            normalized_task_id,
            resource_id=resource_filter or None,
            page=page,
            page_size=page_size,
        )
        if normalized_task_id
        else None
    )
    entry_items = entries_page_dto.items if entries_page_dto is not None else ()
    resolved_time_entry_id = resolve_time_entry_id(selected_time_entry_id, entry_items)
    selected_entry_dto = next(
        (item for item in entry_items if item.entry_id == resolved_time_entry_id),
        None,
    )

    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_task_id=normalized_task_id,
        assignment_options=assignment_options,
        task_time_summary=build_task_time_summary_dict(summary_dto),
        task_time_entries_page=build_task_time_entries_page_dict(entries_page_dto),
        task_time_entries_resource_filter=resource_filter,
        task_time_entries_page_number=page,
        selected_time_entry_id=resolved_time_entry_id,
        selected_time_entry_detail=build_selected_time_entry_detail(selected_entry_dto),
    )


def build_empty_task_time_state() -> TaskCatalogWorkspaceViewModel:
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        task_time_summary=None,
        task_time_entries_page=None,
        selected_time_entry_id="",
        selected_time_entry_detail=build_selected_time_entry_detail(None),
    )


def build_task_time_entries_refresh(
    desktop_api,
    *,
    task_id: str,
    resource_filter: str = "",
    page: int = 1,
    page_size: int = 25,
    selected_time_entry_id: str | None = None,
) -> TaskCatalogWorkspaceViewModel | None:
    """Fast path after an entry-level mutation: re-fetch the task-scoped
    summary + entries page only, skip assignment-options rebuild."""
    if not task_id:
        return None
    try:
        summary_dto = desktop_api.get_task_time_summary(task_id)
        entries_page_dto = desktop_api.list_task_time_entries(
            task_id,
            resource_id=resource_filter or None,
            page=page,
            page_size=page_size,
        )
    except Exception:
        return None
    entry_items = entries_page_dto.items if entries_page_dto is not None else ()
    resolved_time_entry_id = resolve_time_entry_id(selected_time_entry_id, entry_items)
    selected_entry_dto = next(
        (item for item in entry_items if item.entry_id == resolved_time_entry_id),
        None,
    )
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_task_id=task_id,
        task_time_summary=build_task_time_summary_dict(summary_dto),
        task_time_entries_page=build_task_time_entries_page_dict(entries_page_dto),
        task_time_entries_resource_filter=resource_filter,
        task_time_entries_page_number=page,
        selected_time_entry_id=resolved_time_entry_id or "",
        selected_time_entry_detail=build_selected_time_entry_detail(selected_entry_dto),
    )


__all__ = [
    "build_empty_task_time_state",
    "build_selected_time_entry_detail",
    "build_task_time_entries_page_dict",
    "build_task_time_entries_refresh",
    "build_task_time_state",
    "build_task_time_summary_dict",
]
