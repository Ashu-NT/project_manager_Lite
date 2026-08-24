from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetRecordViewModel,
)

def to_review_queue_record(row: Any) -> TimesheetRecordViewModel:
    return TimesheetRecordViewModel(
        id=row.period_id,
        title=f"{row.resource_name} | {row.period_start_label}",
        status_label=row.status_label,
        subtitle=", ".join(row.project_names) if row.project_names else "Shared / cross-project scope",
        supporting_text=f"{row.total_hours_label} across {row.entry_count} entry or entries.",
        meta_text=f"Submitted by {row.submitted_by_username} at {row.submitted_at_label}",
        can_primary_action=bool(getattr(row, "can_approve", False)),
        can_secondary_action=bool(getattr(row, "can_reject", False)),
        can_tertiary_action=bool(
            getattr(row, "can_lock", False) or getattr(row, "can_unlock", False)
        ),
        state={
            "periodId": row.period_id,
            "resourceId": row.resource_id,
            "periodStart": row.period_start.isoformat(),
            "status": row.status,
            "version": getattr(row, "version", 1),
            "canApprove": bool(getattr(row, "can_approve", False)),
            "canReject": bool(getattr(row, "can_reject", False)),
            "canLock": bool(getattr(row, "can_lock", False)),
            "canUnlock": bool(getattr(row, "can_unlock", False)),
            "totalHours": getattr(row, "total_hours", 0.0),
            "projectCount": getattr(row, "project_count", len(row.project_names)),
            "taskCount": getattr(row, "task_count", 0),
            "entryCount": row.entry_count,
            "genericEntryCount": getattr(row, "generic_entry_count", 0),
        },
    )
