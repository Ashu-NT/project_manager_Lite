from __future__ import annotations

from typing import Any

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
    total: int,
    filtered_total: int,
    in_progress: int,
    blocked: int,
    done: int,
    overdue: int,
    collaboration_workspace_snapshot: Any,
    collaboration_snapshot: Any,
    has_selected_task: bool,
) -> TaskCatalogOverviewViewModel:
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
                value=str(total),
                supporting_text=(
                    f"Showing {filtered_total} with the current filters."
                ),
            ),
            TaskCatalogMetricViewModel(
                label="In progress",
                value=str(in_progress),
                supporting_text="Active execution tasks.",
            ),
            TaskCatalogMetricViewModel(
                label="Blocked",
                value=str(blocked),
                supporting_text="Needs intervention.",
            ),
            TaskCatalogMetricViewModel(
                label="Done",
                value=str(done),
                supporting_text="Completed scope.",
            ),
            TaskCatalogMetricViewModel(
                label="Overdue",
                value=str(overdue),
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
