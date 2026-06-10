from __future__ import annotations


def resolve_selected_resource_id(
    selected_resource_id: str | None,
    filtered_resources,
) -> str:
    normalized_id = (selected_resource_id or "").strip()
    if normalized_id and any(resource.id == normalized_id for resource in filtered_resources):
        return normalized_id
    if filtered_resources:
        return filtered_resources[0].id
    return ""
