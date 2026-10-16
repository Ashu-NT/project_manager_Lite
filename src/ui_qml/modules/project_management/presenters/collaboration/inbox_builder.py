from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import body_preview, iso_datetime, mentions_label


def build_inbox_collection(
    items,
    *,
    total_count: int,
    page: int,
    page_size: int,
) -> CollaborationCollectionViewModel:
    return CollaborationCollectionViewModel(
        title="Inbox",
        subtitle="Principal-scoped collaboration items requiring your awareness.",
        empty_state="No collaboration inbox items match the current scope.",
        total_count=total_count,
        page=page,
        page_size=page_size,
        items=tuple(
            CollaborationRecordViewModel(
                id=f"inbox:{item.comment_id}",
                title=item.task_name,
                status_label="Unread" if item.unread else "Read",
                subtitle=item.project_name,
                supporting_text=body_preview(item) or mentions_label(item.mentions),
                meta_text=f"{item.created_at.strftime('%Y-%m-%d %H:%M')} | @{item.author_username}",
                can_primary_action=item.unread,
                state={
                    "panelId": "inbox",
                    "routeId": "project_management.tasks",
                    "projectId": item.project_id,
                    "projectName": item.project_name,
                    "taskId": item.task_id,
                    "commentId": item.comment_id,
                    "actorUsername": item.author_username,
                    "unread": item.unread,
                    "attention": item.unread,
                    "createdAt": iso_datetime(item.created_at),
                },
            )
            for item in items
        ),
    )


__all__ = ["build_inbox_collection"]
