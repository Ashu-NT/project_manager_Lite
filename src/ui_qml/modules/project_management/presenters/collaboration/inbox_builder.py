from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import iso_datetime
from .routing import notification_route_id


def build_inbox_collection(notifications) -> CollaborationCollectionViewModel:
    return CollaborationCollectionViewModel(
        title="Inbox",
        subtitle="Operational workflow inbox for mentions, approvals, timesheets, and PM alerts.",
        empty_state="No workflow inbox items are visible right now.",
        items=tuple(
            CollaborationRecordViewModel(
                id=f"inbox:{n.entity_type}:{n.entity_id}",
                title=n.headline,
                status_label=(
                    "Needs Attention" if n.attention else n.notification_type_label
                ),
                subtitle=" | ".join(
                    value
                    for value in (
                        n.notification_type_label,
                        n.project_name or "Cross-project",
                    )
                    if value
                ),
                supporting_text=n.body_preview or "No preview available.",
                meta_text=f"From @{n.actor_username} | {n.created_at_label}",
                can_primary_action=n.attention,
                state={
                    "panelId": "inbox",
                    "routeId": notification_route_id(n),
                    "projectId": n.project_id or "",
                    "projectName": n.project_name or "",
                    "taskId": getattr(n, "task_id", "") or "",
                    "entityId": n.entity_id,
                    "entityType": n.entity_type,
                    "notificationType": n.notification_type,
                    "actorUsername": n.actor_username,
                    "attention": n.attention,
                    "createdAt": iso_datetime(n.created_at),
                },
            )
            for n in notifications
        ),
    )
