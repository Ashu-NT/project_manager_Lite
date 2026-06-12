from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import iso_datetime


def build_mentions_collection(inbox) -> CollaborationCollectionViewModel:
    return CollaborationCollectionViewModel(
        title="Mentions",
        subtitle="Direct mentions needing follow-up or acknowledgment.",
        empty_state="No direct mentions need review right now.",
        items=tuple(
            CollaborationRecordViewModel(
                id=item.comment_id,
                title=item.task_name,
                status_label="Unread" if item.unread else "Read",
                subtitle=" | ".join(
                    value
                    for value in (item.task_name, item.project_name)
                    if value
                ),
                supporting_text=f"From @{item.author_username} | {item.mentions_label}",
                meta_text=item.created_at_label,
                can_primary_action=item.unread,
                state={
                    "panelId": "mentions",
                    "routeId": "project_management.tasks",
                    "projectId": item.project_id,
                    "projectName": item.project_name,
                    "taskId": item.task_id,
                    "commentId": item.comment_id,
                    "actorUsername": item.author_username,
                    "mentionsLabel": item.mentions_label,
                    "unread": item.unread,
                    "createdAt": iso_datetime(item.created_at),
                },
            )
            for item in inbox
        ),
    )
