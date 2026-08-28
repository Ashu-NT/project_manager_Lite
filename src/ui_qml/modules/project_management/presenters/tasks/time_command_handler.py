from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
)

from .validation import optional_int, optional_text, require_date, require_float, require_text


def _require_expected_version(value: object) -> int:
    version = optional_int({"expectedVersion": value}, "expectedVersion")
    if version is None or version < 1:
        raise ValueError("Refresh the time entry before changing it.")
    return version

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
        expected_version=_require_expected_version(payload.get("expectedVersion")),
        entry_date=require_date(payload, "entryDate", "Entry date is required."),
        hours=require_float(payload, "hours", "Hours are required."),
        note=optional_text(payload, "note") or "",
    )
    timesheets_desktop_api.update_time_entry(command)

def delete_task_time_entry(
    timesheets_desktop_api,
    entry_id: str,
    expected_version: int,
) -> None:
    normalized_entry_id = (entry_id or "").strip()
    if not normalized_entry_id:
        raise ValueError("Choose an entry to delete.")
    timesheets_desktop_api.delete_time_entry(
        normalized_entry_id,
        expected_version=_require_expected_version(expected_version),
    )
