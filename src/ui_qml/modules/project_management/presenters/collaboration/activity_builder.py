from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import iso_datetime
from .routing import notification_route_id
from .utils import sort_records_by_created_desc


def build_activity_collection(
    *,
    notifications,
    recent_activity,
) -> CollaborationCollectionViewModel:
    rows: list[CollaborationRecordViewModel] = []
    for n in notifications:
        rows.append(
            CollaborationRecordViewModel(
                id=f"activity-note:{n.entity_type}:{n.entity_id}",
                title=n.headline,
                status_label=n.notification_type_label,
                subtitle=n.project_name or "Cross-project activity",
                supporting_text=n.body_preview or f"From @{n.actor_username}",
                meta_text=n.created_at_label,
                state={
                    "panelId": "activity",
                    "routeId": notification_route_id(n),
                    "projectId": n.project_id or "",
                    "projectName": n.project_name or "",
                    "actorUsername": n.actor_username,
                    "entityId": n.entity_id,
                    "entityType": n.entity_type,
                    "createdAt": iso_datetime(n.created_at),
                },
            )
        )
    for item in recent_activity:
        rows.append(
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
                    "mentionsLabel": item.mentions_label,
                    "createdAt": iso_datetime(item.created_at),
                },
            )
        )
    return CollaborationCollectionViewModel(
        title="Activity",
        subtitle="Workflow and collaboration activity across accessible project operations.",
        empty_state="No workflow activity is available yet.",
        items=sort_records_by_created_desc(tuple(rows)),
    )
