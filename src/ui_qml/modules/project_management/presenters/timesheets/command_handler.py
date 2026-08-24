from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementTimesheetsDesktopApi,
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
)

from .validation import (
    optional_text,
    require_date,
    require_float,
    require_positive_int,
    require_text,
)

def add_time_entry(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = TimesheetEntryCreateCommand(
        assignment_id=require_text(payload, "assignmentId", "Choose an assignment first."),
        entry_date=require_date(payload, "entryDate", "Entry date is required."),
        hours=require_float(payload, "hours", "Hours are required."),
        note=optional_text(payload, "note") or "",
    )
    desktop_api.add_time_entry(command)

def update_time_entry(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = TimesheetEntryUpdateCommand(
        entry_id=require_text(payload, "entryId", "Choose an entry to update."),
        entry_date=require_date(payload, "entryDate", "Entry date is required."),
        hours=require_float(payload, "hours", "Hours are required."),
        note=optional_text(payload, "note") or "",
    )
    desktop_api.update_time_entry(command)

def delete_time_entry(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    entry_id: str,
) -> None:
    normalized_entry_id = (entry_id or "").strip()
    if not normalized_entry_id:
        raise ValueError("Choose an entry to delete.")
    desktop_api.delete_time_entry(normalized_entry_id)

def submit_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.submit_period(
        resource_id=require_text(payload, "resourceId", "Choose a resource period to submit."),
        period_start=require_date(payload, "periodStart", "Period start is required."),
        note=optional_text(payload, "note") or "",
    )

def approve_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.approve_period(
        require_text(payload, "periodId", "Choose a period to approve."),
        expected_version=require_positive_int(
            payload, "expectedVersion", "Refresh the period before approving it."
        ),
        note=optional_text(payload, "note") or "",
    )

def reject_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.reject_period(
        require_text(payload, "periodId", "Choose a period to reject."),
        expected_version=require_positive_int(
            payload, "expectedVersion", "Refresh the period before returning it."
        ),
        note=require_text(payload, "note", "A return reason is required."),
    )

def lock_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.lock_period(
        require_text(payload, "periodId", "Choose a period to lock."),
        expected_version=require_positive_int(
            payload, "expectedVersion", "Refresh the period before locking it."
        ),
        note=optional_text(payload, "note") or "",
    )

def unlock_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.unlock_period(
        require_text(payload, "periodId", "Choose a period to unlock."),
        expected_version=require_positive_int(
            payload, "expectedVersion", "Refresh the period before unlocking it."
        ),
        note=optional_text(payload, "note") or "",
    )
