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
    entry_titles = ", ".join(entry.task_name for entry in detail.entries[:3])
    if len(detail.entries) > 3:
        entry_titles += ", ..."
    if not entry_titles:
        entry_titles = "No review entries recorded."
    return TimesheetDetailViewModel(
        id=summary.period_id,
        title=f"{summary.resource_name} | {summary.period_start_label}",
        status_label=summary.status_label,
        subtitle=" | ".join(summary.project_names) if summary.project_names else "Shared / cross-project scope",
        description=entry_titles,
        fields=(
            TimesheetDetailFieldViewModel(
                label="Hours",
                value=summary.total_hours_label,
                supporting_text=f"{summary.entry_count} entry or entries.",
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
        },
    )
