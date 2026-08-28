from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_hours,
)
from src.core.modules.project_management.api.desktop.timesheets.formatters.time_formatter import (
    format_hours as format_entry_hours,
)
from src.core.modules.project_management.api.desktop.tasks.models.time_summary import (
    TaskResourceTimeBreakdownDesktopDto,
    TaskTimeEntriesPageDesktopDto,
    TaskTimeEntryDesktopDto,
    TaskTimeSummaryDesktopDto,
)


def _burn_status_label(burn_status: str) -> str:
    return burn_status.replace("_", " ").title()


def serialize_task_time_summary(fact) -> TaskTimeSummaryDesktopDto:
    return TaskTimeSummaryDesktopDto(
        task_id=fact.task_id,
        planned_hours_label=format_hours(fact.planned_hours),
        actual_hours_label=format_hours(fact.actual_hours),
        remaining_hours_label=format_hours(fact.remaining_hours),
        overrun_hours_label=format_hours(fact.overrun_hours),
        has_overrun=fact.overrun_hours > 0,
        burn_status=fact.burn_status,
        burn_status_label=_burn_status_label(fact.burn_status),
        assignment_count=fact.assignment_count,
        resource_breakdown=tuple(
            TaskResourceTimeBreakdownDesktopDto(
                assignment_id=row.assignment_id,
                resource_id=row.resource_id,
                resource_name=row.resource_name,
                planned_hours_label=format_hours(row.planned_hours),
                actual_hours_label=format_hours(row.actual_hours),
                remaining_hours_label=format_hours(row.remaining_hours),
                overrun_hours_label=format_hours(row.overrun_hours),
                has_overrun=row.overrun_hours > 0,
                burn_status=row.burn_status,
                burn_status_label=_burn_status_label(row.burn_status),
            )
            for row in fact.resource_breakdown
        ),
    )


def serialize_task_time_entries_page(page, *, resources_by_id: dict[str, object]) -> TaskTimeEntriesPageDesktopDto:
    return TaskTimeEntriesPageDesktopDto(
        items=tuple(
            TaskTimeEntryDesktopDto(
                entry_id=row.entry_id,
                assignment_id=row.work_allocation_id,
                resource_id=row.resource_id,
                resource_name=getattr(
                    resources_by_id.get(row.resource_id), "name", ""
                ) or row.resource_id,
                entry_date_label=row.entry_date.isoformat(),
                hours=float(row.hours or 0.0),
                hours_label=format_entry_hours(row.hours),
                note=row.note or "",
                author_username=row.author_username or "unknown",
                version=row.version,
            )
            for row in page.items
        ),
        total=page.total,
        page=page.page,
        page_size=page.page_size,
    )


__all__ = ["serialize_task_time_entries_page", "serialize_task_time_summary"]
