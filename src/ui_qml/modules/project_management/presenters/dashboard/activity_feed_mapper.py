from __future__ import annotations

from src.ui_qml.modules.project_management.presenters.dashboard.formatters.date_formatter import (
    coerce_utc_datetime,
    fmt_utc_datetime,
)
from src.ui_qml.shared.models.activity_item import ActivityItemViewModel


def to_activity_item(activity) -> ActivityItemViewModel:
    is_mention = bool(getattr(activity, "mentions", ()))
    created_at = coerce_utc_datetime(getattr(activity, "created_at", None))
    return ActivityItemViewModel(
        id=f"comment-{getattr(activity, 'comment_id', '')}",
        title=f"{getattr(activity, 'task_name', '') or 'Task'} update",
        actor_display=getattr(activity, "author_username", "") or "System",
        occurred_at=created_at, occurred_at_label=fmt_utc_datetime(created_at),
        icon_key="collaboration", tone="info" if is_mention else "neutral",
        subject_display=getattr(activity, "project_name", "") or "",
        badge_label="Mention" if is_mention else "",
        activation_state={
            "routeId": "project_management.tasks",
            "taskId": getattr(activity, "task_id", ""),
            "projectId": getattr(activity, "project_id", ""),
            "commentId": getattr(activity, "comment_id", ""),
        },
    )
