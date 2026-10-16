from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.time_summary import (
    TaskTimeEntriesPageDesktopDto,
    TaskTimeEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.formatters.time_formatter import (
    format_hours as format_entry_hours,
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


__all__ = ["serialize_task_time_entries_page"]
