from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import iso_datetime


def build_active_presence_collection(active_presence) -> CollaborationCollectionViewModel:
    return CollaborationCollectionViewModel(
        title="Active Now",
        subtitle="People currently active in PM task collaboration and review flows.",
        empty_state="No active collaboration presence is visible right now.",
        items=tuple(
            CollaborationRecordViewModel(
                id=f"{item.task_id}:{item.username}",
                title=item.task_name,
                status_label=item.activity_label,
                subtitle=item.project_name,
                supporting_text=item.who_label,
                meta_text=(
                    f"Last seen {item.last_seen_at_label}"
                    + (" | You" if item.is_self else "")
                ),
                state={
                    "panelId": "team_updates",
                    "routeId": "project_management.tasks",
                    "projectId": item.project_id,
                    "projectName": item.project_name,
                    "taskId": item.task_id,
                    "taskName": item.task_name,
                    "username": item.username,
                    "displayName": item.display_name or "",
                    "activity": item.activity,
                    "createdAt": iso_datetime(item.last_seen_at),
                },
            )
            for item in active_presence
        ),
    )
