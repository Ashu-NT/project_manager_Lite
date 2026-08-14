from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import iso_datetime


def build_activity_collection(recent_activity) -> CollaborationCollectionViewModel:
    return CollaborationCollectionViewModel(
        title="Activity",
        subtitle="The 100 most recent task comments in the selected collaboration scope.",
        empty_state="No recent collaboration activity matches the current scope.",
        items=tuple(
            CollaborationRecordViewModel(
                id=f"activity-comment:{item.comment_id}",
                title=item.task_name,
                status_label="Mention" if item.mentions else "Comment",
                subtitle=item.project_name,
                supporting_text=item.body_preview or item.mentions_label,
                meta_text=f"{item.created_at_label} | @{item.author_username}",
                state={
                    "panelId": "activity",
                    "routeId": "project_management.tasks",
                    "projectId": item.project_id,
                    "projectName": item.project_name,
                    "taskId": item.task_id,
                    "commentId": item.comment_id,
                    "actorUsername": item.author_username,
                    "createdAt": iso_datetime(item.created_at),
                },
            )
            for item in recent_activity
        ),
    )


__all__ = ["build_activity_collection"]
