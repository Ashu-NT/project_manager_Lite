from __future__ import annotations

from src.ui_qml.shared.models.activity_item import ActivityItemViewModel, serialize_activity_items

from .formatting import format_timestamp


def build_activity_collection(recent_activity) -> dict[str, object]:
    return {
        "title": "Activity",
        "subtitle": "The 100 most recent task comments in the selected collaboration scope.",
        "emptyState": "No recent collaboration activity matches the current scope.",
        "items": serialize_activity_items(_to_activity_item(item) for item in recent_activity),
    }


def _to_activity_item(item) -> ActivityItemViewModel:
    is_mention = bool(item.mentions)
    return ActivityItemViewModel(
        id=f"activity-comment:{item.comment_id}",
        title=item.task_name,
        description=item.body_preview or item.mentions_label,
        actor_display=item.author_username or "System",
        occurred_at=item.created_at,
        occurred_at_label=format_timestamp(item.created_at),
        icon_key="collaboration",
        tone="info" if is_mention else "neutral",
        subject_display=item.project_name,
        status_label="Mention" if is_mention else "",
        activation_state={
            "routeId": "project_management.tasks",
            "projectId": item.project_id,
            "projectName": item.project_name,
            "taskId": item.task_id,
            "commentId": item.comment_id,
            "actorUsername": item.author_username,
            "createdAt": item.created_at.isoformat() if item.created_at else "",
        },
    )


__all__ = ["build_activity_collection"]
