from __future__ import annotations

from datetime import date

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogMetricViewModel,
    TaskCatalogOverviewViewModel,
)


def build_empty_overview() -> TaskCatalogOverviewViewModel:
    return TaskCatalogOverviewViewModel(
        title="Tasks",
        subtitle=(
            "Task planning, progress, dependencies, assignments, "
            "and execution state."
        ),
        metrics=(),
    )


def build_overview(
    *,
    all_tasks,
    filtered_tasks,
    collaboration_workspace_snapshot,
    collaboration_snapshot,
    has_selected_task: bool,
) -> TaskCatalogOverviewViewModel:
    today = date.today()

    def count_by_status(status: str) -> int:
        return sum(1 for task in all_tasks if task.status == status)

    overdue_count = sum(
        1
        for task in all_tasks
        if task.deadline is not None
        and task.deadline < today
        and task.status != "DONE"
    )
    unread_mentions_count = sum(
        1
        for item in getattr(collaboration_workspace_snapshot, "inbox", ())
        if bool(getattr(item, "unread", False))
    )
    notification_count = len(
        getattr(collaboration_workspace_snapshot, "notifications", ())
    )
    active_presence_count = len(
        getattr(collaboration_snapshot, "active_presence", ())
        if collaboration_snapshot is not None
        else ()
    )
    return TaskCatalogOverviewViewModel(
        title="Tasks",
        subtitle=(
            "Task planning, progress, dependencies, assignments, and "
            "execution state."
        ),
        metrics=(
            TaskCatalogMetricViewModel(
                label="Total tasks",
                value=str(len(all_tasks)),
                supporting_text=(
                    f"Showing {len(filtered_tasks)} with the current filters."
                ),
            ),
            TaskCatalogMetricViewModel(
                label="In progress",
                value=str(count_by_status("IN_PROGRESS")),
                supporting_text="Active execution tasks.",
            ),
            TaskCatalogMetricViewModel(
                label="Blocked",
                value=str(count_by_status("BLOCKED")),
                supporting_text="Needs intervention.",
            ),
            TaskCatalogMetricViewModel(
                label="Done",
                value=str(count_by_status("DONE")),
                supporting_text="Completed scope.",
            ),
            TaskCatalogMetricViewModel(
                label="Overdue",
                value=str(overdue_count),
                supporting_text="Past deadline and not done.",
            ),
            TaskCatalogMetricViewModel(
                label="Mentions",
                value=str(unread_mentions_count),
                supporting_text="Unread task mentions across accessible projects.",
            ),
            TaskCatalogMetricViewModel(
                label="Notifications",
                value=str(notification_count),
                supporting_text="Workflow alerts from approvals, timesheets, and mentions.",
            ),
            TaskCatalogMetricViewModel(
                label="Active now",
                value=str(active_presence_count),
                supporting_text=(
                    "People currently active on the selected task."
                    if has_selected_task
                    else "Select a task to see active collaborators."
                ),
            ),
        ),
    )
