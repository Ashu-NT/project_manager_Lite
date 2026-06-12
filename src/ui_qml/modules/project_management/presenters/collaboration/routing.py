from __future__ import annotations

from typing import Any

def notification_route_id(notification: Any) -> str:
    entity_type = str(getattr(notification, "entity_type", "") or "")
    notification_type = str(getattr(notification, "notification_type", "") or "")
    if entity_type == "approval_request":
        return "platform.control"
    if notification_type == "timesheet":
        return "project_management.timesheets"
    if entity_type == "task_comment" or notification_type == "mention":
        return "project_management.tasks"
    return "project_management.collaboration"
