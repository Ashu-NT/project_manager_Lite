from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import iso_datetime


def build_team_updates_collection(active_presence) -> CollaborationCollectionViewModel:
    return CollaborationCollectionViewModel(
        title="Team Updates",
        subtitle="Active users currently editing, reviewing, or monitoring PM task workflows.",
        empty_state="No active collaboration presence is visible right now.",
        items=tuple(
            CollaborationRecordViewModel(
                id=f"{item.task_id}:{item.username}",
                title=item.who_label,
                status_label=item.activity_label,
                subtitle=" | ".join(
                    value
                    for value in (item.task_name, item.project_name)
                    if value
                ),
                supporting_text=f"Last seen {item.last_seen_at_label}",
                meta_text="You" if item.is_self else f"@{item.username}",
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
