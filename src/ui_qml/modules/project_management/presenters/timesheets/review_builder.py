from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetDetailFieldViewModel,
    TimesheetDetailViewModel,
)


def build_review_detail(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    period_id: str,
) -> TimesheetDetailViewModel:
    if not period_id:
        return TimesheetDetailViewModel(
            title="No review period selected",
            empty_state="Select a review-queue period to inspect its entries and decide approval or rejection.",
        )
    detail = desktop_api.get_review_detail(period_id)
    summary = detail.summary
    return TimesheetDetailViewModel(
        id=summary.period_id,
        title=f"{summary.resource_name} | {summary.period_start_label}",
        status_label=summary.status_label,
        subtitle=" | ".join(summary.project_names) if summary.project_names else "Shared / cross-project scope",
        description="Decision context for this authoritative timesheet period.",
        fields=(
            TimesheetDetailFieldViewModel(
                label="Hours",
                value=summary.total_hours_label,
                supporting_text=f"{summary.entry_count} entry or entries.",
            ),
            TimesheetDetailFieldViewModel(
                label="Allocation context",
                value=f"{getattr(summary, 'project_count', len(summary.project_names))} project(s) | {getattr(summary, 'task_count', 0)} task(s)",
                supporting_text=(
                    f"{getattr(summary, 'generic_entry_count', 0)} generic or non-task entry/entries."
                    if getattr(summary, "generic_entry_count", 0)
                    else "All entries have task attribution."
                ),
            ),
            TimesheetDetailFieldViewModel(
                label="Submitted by",
                value=summary.submitted_by_username,
                supporting_text=summary.submitted_at_label,
            ),
            TimesheetDetailFieldViewModel(
                label="Decided by",
                value=summary.decided_by_username,
                supporting_text=summary.decided_at_label,
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
            "status": summary.status,
            "version": getattr(summary, "version", 1),
            "canApprove": bool(getattr(summary, "can_approve", False)),
            "canReject": bool(getattr(summary, "can_reject", False)),
            "canLock": bool(getattr(summary, "can_lock", False)),
            "canUnlock": bool(getattr(summary, "can_unlock", False)),
            "totalHoursLabel": summary.total_hours_label,
            "submittedBy": summary.submitted_by_username,
            "submittedAt": summary.submitted_at_label,
            "decidedBy": summary.decided_by_username,
            "decidedAt": summary.decided_at_label,
            "decisionNote": summary.decision_note,
        },
    )
