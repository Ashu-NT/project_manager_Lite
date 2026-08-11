from __future__ import annotations

from typing import Any

def resolve_project_id(
    selected_project_id: str | None,
    project_options: Any,
) -> str:
    normalized_value = (selected_project_id or "").strip()
    if normalized_value and any(
        option.value == normalized_value for option in project_options
    ):
        return normalized_value
    if project_options:
        return project_options[0].value
    return ""

