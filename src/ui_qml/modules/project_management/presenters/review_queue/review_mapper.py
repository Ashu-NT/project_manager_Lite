from __future__ import annotations

from collections.abc import Mapping

from src.core.modules.project_management.contracts.reads.timesheets.review_reader import (
    TimesheetReviewQueueFact,
)
from src.ui_qml.modules.project_management.presenters.review_queue.formatting import (
    format_datetime,
    format_hours,
    format_period_label,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetRecordViewModel,
)


def to_review_queue_record(
    row: TimesheetReviewQueueFact, *, project_labels: Mapping[str, str]
) -> TimesheetRecordViewModel:
    project_names = tuple(
        project_labels.get(project_id, project_id) for project_id in row.project_ids
    )
    return TimesheetRecordViewModel(
        id=row.period_id,
        title=f"{row.resource_name} | {format_period_label(row.period_start)}",
        status_label=row.status.value.replace("_", " ").title(),
        subtitle=", ".join(project_names)
        if project_names
        else "Shared / cross-project scope",
        supporting_text=f"{format_hours(row.total_hours)} across {row.entry_count} entry or entries.",
        meta_text=f"Submitted by {row.submitted_by_username or '-'} at {format_datetime(row.submitted_at)}",
        can_primary_action=bool(getattr(row, "can_approve", False)),
        can_secondary_action=bool(getattr(row, "can_reject", False)),
        can_tertiary_action=bool(
            getattr(row, "can_lock", False) or getattr(row, "can_unlock", False)
        ),
        state={
            "periodId": row.period_id,
            "resourceId": row.resource_id,
            "periodStart": row.period_start.isoformat(),
            "status": row.status.value,
            "version": getattr(row, "version", 1),
            "canApprove": bool(getattr(row, "can_approve", False)),
            "canReject": bool(getattr(row, "can_reject", False)),
            "canLock": bool(getattr(row, "can_lock", False)),
            "canUnlock": bool(getattr(row, "can_unlock", False)),
            "totalHours": getattr(row, "total_hours", 0.0),
            "projectCount": getattr(row, "project_count", len(project_names)),
            "taskCount": getattr(row, "task_count", 0),
            "entryCount": row.entry_count,
            "genericEntryCount": getattr(row, "generic_entry_count", 0),
        },
    )
