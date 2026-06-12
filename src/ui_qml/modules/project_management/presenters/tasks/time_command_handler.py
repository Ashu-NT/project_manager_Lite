from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
)

from .validation import optional_text, require_date, require_float, require_text

def add_task_time_entry(timesheets_desktop_api, payload: dict[str, Any]) -> None:
    command = TimesheetEntryCreateCommand(
        assignment_id=require_text(
            payload, "assignmentId", "Choose an assignment before logging time."
        ),
        entry_date=require_date(payload, "entryDate", "Entry date is required."),
        hours=require_float(payload, "hours", "Hours are required."),
        note=optional_text(payload, "note") or "",
    )
    timesheets_desktop_api.add_time_entry(command)

def update_task_time_entry(timesheets_desktop_api, payload: dict[str, Any]) -> None:
    command = TimesheetEntryUpdateCommand(
        entry_id=require_text(payload, "entryId", "Choose an entry to update."),
        entry_date=require_date(payload, "entryDate", "Entry date is required."),
        hours=require_float(payload, "hours", "Hours are required."),
        note=optional_text(payload, "note") or "",
    )
    timesheets_desktop_api.update_time_entry(command)

def delete_task_time_entry(timesheets_desktop_api, entry_id: str) -> None:
    normalized_entry_id = (entry_id or "").strip()
    if not normalized_entry_id:
        raise ValueError("Choose an entry to delete.")
    timesheets_desktop_api.delete_time_entry(normalized_entry_id)

def submit_task_period(timesheets_desktop_api, payload: dict[str, Any]) -> None:
    timesheets_desktop_api.submit_period(
        resource_id=require_text(
            payload, "resourceId", "Choose a resource period to submit."
        ),
        period_start=require_date(payload, "periodStart", "Period start is required."),
        note=optional_text(payload, "note") or "",
    )

def lock_task_period(timesheets_desktop_api, payload: dict[str, Any]) -> None:
    timesheets_desktop_api.lock_period(
        resource_id=require_text(
            payload, "resourceId", "Choose a resource period to lock."
        ),
        period_start=require_date(payload, "periodStart", "Period start is required."),
        note=optional_text(payload, "note") or "",
    )

def unlock_task_period(timesheets_desktop_api, payload: dict[str, Any]) -> None:
    timesheets_desktop_api.unlock_period(
        require_text(payload, "periodId", "Choose a period to unlock."),
        note=optional_text(payload, "note") or "",
    )
