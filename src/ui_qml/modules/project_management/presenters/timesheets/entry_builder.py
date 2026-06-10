from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetDetailFieldViewModel,
    TimesheetDetailViewModel,
)


def build_selected_entry_detail(selected_entry) -> TimesheetDetailViewModel:
    if selected_entry is None:
        return TimesheetDetailViewModel(
            title="No entry selected",
            empty_state="Select an entry from the period list to review or edit its captured labor note.",
        )
    return TimesheetDetailViewModel(
        id=selected_entry.entry_id,
        title=selected_entry.entry_date_label,
        status_label=selected_entry.hours_label,
        subtitle=selected_entry.author_username,
        description=selected_entry.note or "No labor note recorded.",
        fields=(
            TimesheetDetailFieldViewModel(label="Date", value=selected_entry.entry_date_label),
            TimesheetDetailFieldViewModel(label="Hours", value=selected_entry.hours_label),
            TimesheetDetailFieldViewModel(label="Author", value=selected_entry.author_username),
        ),
        state={
            "entryId": selected_entry.entry_id,
            "entryDate": selected_entry.entry_date_label,
            "hours": str(selected_entry.hours),
            "note": selected_entry.note,
        },
    )
