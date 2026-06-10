from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetRecordViewModel,
)


def to_review_queue_record(row) -> TimesheetRecordViewModel:
    return TimesheetRecordViewModel(
        id=row.period_id,
        title=f"{row.resource_name} | {row.period_start_label}",
        status_label=row.status_label,
        subtitle=", ".join(row.project_names) if row.project_names else "Shared / cross-project scope",
        supporting_text=f"{row.total_hours_label} across {row.entry_count} entry or entries.",
        meta_text=f"Submitted by {row.submitted_by_username} at {row.submitted_at_label}",
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "periodId": row.period_id,
            "resourceId": row.resource_id,
            "periodStart": row.period_start.isoformat(),
            "status": row.status,
        },
    )
