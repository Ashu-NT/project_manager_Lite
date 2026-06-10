from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetMetricViewModel,
    TimesheetOverviewViewModel,
)


def build_overview(
    *,
    assignment_options,
    snapshot,
    review_queue_rows,
) -> TimesheetOverviewViewModel:
    return TimesheetOverviewViewModel(
        title="Timesheets",
        subtitle="Labor capture, month-end period status, and approver review from one PM workspace.",
        metrics=(
            TimesheetMetricViewModel(
                label="Assignments",
                value=str(len(assignment_options)),
                supporting_text="Assignments available inside the current project scope.",
            ),
            TimesheetMetricViewModel(
                label="Period entries",
                value=str(len(snapshot.entries) if snapshot is not None else 0),
                supporting_text=(
                    snapshot.scope_summary
                    if snapshot is not None
                    else "Select an assignment to inspect period hours."
                ),
            ),
            TimesheetMetricViewModel(
                label="Review queue",
                value=str(len(review_queue_rows)),
                supporting_text="Periods currently visible in the review lane.",
            ),
            TimesheetMetricViewModel(
                label="Selected period",
                value=(
                    snapshot.period_summary.status_label
                    if snapshot is not None
                    else "Not selected"
                ),
                supporting_text=(
                    snapshot.period_summary.period_start_label
                    if snapshot is not None
                    else "Choose an assignment first."
                ),
            ),
        ),
    )
