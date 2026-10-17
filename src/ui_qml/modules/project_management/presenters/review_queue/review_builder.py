from __future__ import annotations

from collections.abc import Mapping

from src.core.modules.project_management.api.desktop import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.ui_qml.modules.project_management.presenters.review_queue.formatting import (
    format_datetime,
    format_hours,
    format_period_label,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetDetailFieldViewModel,
    TimesheetDetailViewModel,
)


def build_review_detail(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    period_id: str,
    *,
    project_labels: Mapping[str, str],
) -> TimesheetDetailViewModel:
    if not period_id:
        return TimesheetDetailViewModel(
            title="No review period selected",
            empty_state="Select a review-queue period to inspect its entries and decide approval or rejection.",
        )
    detail = desktop_api.get_review_detail(period_id)
    summary = detail.summary
    project_names = tuple(
        project_labels.get(project_id, project_id) for project_id in summary.project_ids
    )
    return TimesheetDetailViewModel(
        id=summary.period_id,
        title=f"{summary.resource_name} | {format_period_label(summary.period_start)}",
        status_label=summary.status.value.replace("_", " ").title(),
        subtitle=" | ".join(project_names)
        if project_names
        else "Shared / cross-project scope",
        description="Decision context for this authoritative timesheet period.",
        fields=(
            TimesheetDetailFieldViewModel(
                label="Hours",
                value=format_hours(summary.total_hours),
                supporting_text=f"{summary.entry_count} entry or entries.",
            ),
            TimesheetDetailFieldViewModel(
                label="Allocation context",
                value=f"{getattr(summary, 'project_count', len(project_names))} project(s) | {getattr(summary, 'task_count', 0)} task(s)",
                supporting_text=(
                    f"{getattr(summary, 'generic_entry_count', 0)} generic or non-task entry/entries."
                    if getattr(summary, "generic_entry_count", 0)
                    else "All entries have task attribution."
                ),
            ),
            TimesheetDetailFieldViewModel(
                label="Submitted by",
                value=summary.submitted_by_username or "-",
                supporting_text=format_datetime(summary.submitted_at),
            ),
            TimesheetDetailFieldViewModel(
                label="Decided by",
                value=summary.decided_by_username or "-",
                supporting_text=format_datetime(summary.decided_at),
            ),
            TimesheetDetailFieldViewModel(
                label="Decision note",
                value=summary.decision_note or "No decision note recorded.",
            ),
        ),
        state={
            "periodId": summary.period_id,
            "resourceId": summary.resource_id,
            "periodStart": summary.period_start.isoformat(),
            "status": summary.status.value,
            "version": getattr(summary, "version", 1),
            "canApprove": bool(getattr(summary, "can_approve", False)),
            "canReject": bool(getattr(summary, "can_reject", False)),
            "canLock": bool(getattr(summary, "can_lock", False)),
            "canUnlock": bool(getattr(summary, "can_unlock", False)),
            "totalHoursLabel": format_hours(summary.total_hours),
            "submittedBy": summary.submitted_by_username,
            "submittedAt": format_datetime(summary.submitted_at),
            "decidedBy": summary.decided_by_username,
            "decidedAt": format_datetime(summary.decided_at),
            "decisionNote": summary.decision_note,
        },
    )
