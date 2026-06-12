from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetRecordViewModel,
)

def to_entry_record(entry: Any) -> TimesheetRecordViewModel:
    return TimesheetRecordViewModel(
        id=entry.entry_id,
        title=entry.entry_date_label,
        status_label=entry.hours_label,
        subtitle=entry.author_username,
        supporting_text=entry.note or "No labor note recorded.",
        meta_text=f"Assignment entry {entry.entry_id}",
        state={
            "entryId": entry.entry_id,
            "entryDate": entry.entry_date_label,
            "hours": entry.hours,
            "note": entry.note,
        },
    )
