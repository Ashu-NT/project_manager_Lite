from __future__ import annotations

from typing import Any

def resolve_selected_project_id(
    selected_project_id: str | None,
    filtered_projects: Any,
) -> str:
    normalized_id = (selected_project_id or "").strip()
    if normalized_id and any(project.id == normalized_id for project in filtered_projects):
        return normalized_id
    if filtered_projects:
        return filtered_projects[0].id
    return ""
