from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetDetailFieldViewModel,
    TimesheetDetailViewModel,
)


def build_assignment_summary(snapshot) -> TimesheetDetailViewModel:
    if snapshot is None:
        return TimesheetDetailViewModel(
            title="No assignment selected",
            empty_state="Select a task assignment to review entries, period status, and labor totals.",
        )
    summary = snapshot.period_summary
    return TimesheetDetailViewModel(
        id=snapshot.assignment.value,
        title=snapshot.assignment.label,
        status_label=summary.status_label,
        subtitle=f"{summary.period_start_label} -> {summary.period_end_label}",
        description=snapshot.scope_summary,
        fields=(
            TimesheetDetailFieldViewModel(
                label="Resource",
                value=summary.resource_name,
            ),
            TimesheetDetailFieldViewModel(
                label="Hours",
                value=summary.total_hours_label,
                supporting_text=f"{summary.entry_count} entry or entries in the selected resource month.",
            ),
            TimesheetDetailFieldViewModel(
                label="Submitted by",
                value=summary.submitted_by_username,
                supporting_text=summary.submitted_at_label,
            ),
            TimesheetDetailFieldViewModel(
                label="Decision",
                value=summary.decided_by_username,
                supporting_text=summary.decided_at_label,
            ),
            TimesheetDetailFieldViewModel(
                label="Decision note",
                value=summary.decision_note or "No review note recorded.",
            ),
        ),
        state={
            "assignmentId": snapshot.assignment.value,
            "resourceId": summary.resource_id,
            "periodStart": snapshot.selected_period_start,
            "periodId": summary.period_id,
            "projectId": snapshot.assignment.project_id,
        },
    )
