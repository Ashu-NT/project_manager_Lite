from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import iso_datetime
from .routing import notification_route_id
from .utils import sort_records_by_created_desc


def build_audit_collection(
    *,
    notifications,
    recent_activity,
) -> CollaborationCollectionViewModel:
    rows: list[CollaborationRecordViewModel] = []
    for n in notifications:
        rows.append(
            CollaborationRecordViewModel(
                id=f"audit-note:{n.entity_type}:{n.entity_id}",
                title=n.headline,
                status_label=n.notification_type_label,
                subtitle=n.project_name or "Cross-project workflow",
                supporting_text=f"From @{n.actor_username}",
                meta_text=n.created_at_label,
                state={
                    "panelId": "audit",
                    "routeId": notification_route_id(n),
                    "projectId": n.project_id or "",
                    "entityId": n.entity_id,
                    "entityType": n.entity_type,
                    "createdAt": iso_datetime(n.created_at),
                },
            )
        )
    for item in recent_activity:
        rows.append(
            CollaborationRecordViewModel(
                id=f"audit-comment:{item.comment_id}",
                title=item.task_name,
                status_label="Comment Trail",
                subtitle=item.project_name,
                supporting_text=item.body_preview or item.mentions_label,
                meta_text=f"{item.created_at_label} | @{item.author_username}",
                state={
                    "panelId": "audit",
                    "routeId": "project_management.tasks",
                    "projectId": item.project_id,
                    "taskId": item.task_id,
                    "commentId": item.comment_id,
                    "createdAt": iso_datetime(item.created_at),
                },
            )
        )
    return CollaborationCollectionViewModel(
        title="Audit",
        subtitle="Trace workflow history, escalations, and collaboration events.",
        empty_state="No workflow audit events are available yet.",
        items=sort_records_by_created_desc(tuple(rows)),
    )
