from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_hours,
)
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
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
    TaskTimeSummaryFact (docs §44 Time redesign) -- rendered as-is,
    never recalculated in QML."""
    if summary_dto is None:
        return None
    return {
        "hasSummary": True,
        "taskId": summary_dto.task_id,
        "plannedHoursLabel": format_hours(summary_dto.planned_hours),
        "actualHoursLabel": format_hours(summary_dto.actual_hours),
        "remainingHoursLabel": format_hours(summary_dto.remaining_hours),
        "overrunHoursLabel": format_hours(summary_dto.overrun_hours),
        "hasOverrun": summary_dto.overrun_hours > 0,
        "burnStatus": summary_dto.burn_status,
        "burnStatusLabel": summary_dto.burn_status.replace("_", " ").title(),
        "assignmentCount": summary_dto.assignment_count,
        "resourceBreakdown": [
            {
                "assignmentId": row.assignment_id,
                "resourceId": row.resource_id,
                "resourceName": row.resource_name,
                "plannedHoursLabel": format_hours(row.planned_hours),
                "actualHoursLabel": format_hours(row.actual_hours),
                "remainingHoursLabel": format_hours(row.remaining_hours),
                "overrunHoursLabel": format_hours(row.overrun_hours),
                "hasOverrun": row.overrun_hours > 0,
                "burnStatus": row.burn_status,
                "burnStatusLabel": row.burn_status.replace("_", " ").title(),
            }
            for row in summary_dto.resource_breakdown
        ],
    }


def build_task_time_entries_page_dict(page_dto, *, resource_names=None) -> dict[str, object] | None:
    """Task-scoped (every assignment on this task), all-time Time Entries
    page straight from TaskTimeEntriesPage (docs §44 Time
    redesign) -- authoritative paging, not a locally-filtered slice of a
    truncated dataset."""
    if page_dto is None:
        return None
    resource_names = resource_names or {}
    return {
        "items": [
            {
                "id": item.entry_id,
                "entryId": item.entry_id,
                "assignmentId": item.work_allocation_id,
                "resourceId": item.resource_id,
                "resourceName": resource_names.get(item.resource_id, item.resource_id),
                "entryDateLabel": item.entry_date.isoformat(),
                "hours": item.hours,
                "hoursLabel": f"{float(item.hours):.2f}h",
                "note": item.note or "",
                "authorUsername": item.author_username or "unknown",
                "version": item.version,
            }
            for item in page_dto.items
        ],
        "total": page_dto.total,
        "page": page_dto.page,
        "pageSize": page_dto.page_size,
    }


def build_selected_time_entry_detail(entry_dto, *, resource_names=None) -> TimesheetDetailViewModel:
    if entry_dto is None:
        return TimesheetDetailViewModel(
            title="No entry selected",
            empty_state=(
                "Select an entry from Time Entries to review or edit its "
                "captured note."
            ),
        )
    resource_names = resource_names or {}
    return TimesheetDetailViewModel(
        id=entry_dto.entry_id,
        title=entry_dto.entry_date.isoformat(),
        status_label=f"{float(entry_dto.hours):.2f}h",
        subtitle=resource_names.get(entry_dto.resource_id, entry_dto.resource_id),
        description=entry_dto.note or "No description recorded.",
        fields=(
            TimesheetDetailFieldViewModel(label="Date", value=entry_dto.entry_date.isoformat()),
            TimesheetDetailFieldViewModel(label="Resource", value=resource_names.get(entry_dto.resource_id, entry_dto.resource_id)),
            TimesheetDetailFieldViewModel(label="Hours", value=f"{float(entry_dto.hours):.2f}h"),
            TimesheetDetailFieldViewModel(
                label="Recorded by", value=entry_dto.author_username or "unknown"
            ),
        ),
        state={
            "entryId": entry_dto.entry_id,
            "assignmentId": entry_dto.work_allocation_id,
            "entryDate": entry_dto.entry_date.isoformat(),
            "hours": str(entry_dto.hours),
            "note": entry_dto.note,
            "authorUsername": entry_dto.author_username or "unknown",
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
    resource_names = {row.resource_id: row.resource_name for row in summary_dto.resource_breakdown} if summary_dto is not None else {}
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
        task_time_entries_page=build_task_time_entries_page_dict(entries_page_dto, resource_names=resource_names),
        task_time_entries_resource_filter=resource_filter,
        task_time_entries_page_number=page,
        selected_time_entry_id=resolved_time_entry_id,
        selected_time_entry_detail=build_selected_time_entry_detail(selected_entry_dto, resource_names=resource_names),
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
    resource_names = {
        row.resource_id: row.resource_name for row in summary_dto.resource_breakdown
    } if summary_dto is not None else {}
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
        task_time_entries_page=build_task_time_entries_page_dict(entries_page_dto, resource_names=resource_names),
        task_time_entries_resource_filter=resource_filter,
        task_time_entries_page_number=page,
        selected_time_entry_id=resolved_time_entry_id or "",
        selected_time_entry_detail=build_selected_time_entry_detail(selected_entry_dto, resource_names=resource_names),
    )


__all__ = [
    "build_empty_task_time_state",
    "build_selected_time_entry_detail",
    "build_task_time_entries_page_dict",
    "build_task_time_entries_refresh",
    "build_task_time_state",
    "build_task_time_summary_dict",
]
