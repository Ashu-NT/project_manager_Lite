from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
)


def build_resource_assignments(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
) -> list[dict[str, object]]:
    normalized_id = (resource_id or "").strip()
    if not normalized_id:
        return []
    assignments = desktop_api.list_resource_assignments(normalized_id)
    return [
        {
            "id": a.id,
            "title": a.task_name,
            "subtitle": a.project_name or "—",
            "statusLabel": a.allocation_label,
            "metaText": a.hours_label,
            "supportingText": a.project_name,
            "state": {
                "taskId": a.task_id,
                "projectId": a.project_id,
                "allocationPercent": a.allocation_percent,
                "hoursLogged": a.hours_logged,
            },
        }
        for a in assignments
    ]
