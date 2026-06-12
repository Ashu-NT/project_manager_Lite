from __future__ import annotations

from typing import Any

def matches_search(resource: Any, search_text: str) -> bool:
    if not search_text:
        return True
    normalized_search = search_text.casefold()
    haystacks = (
        resource.name or "",
        resource.role or "",
        resource.worker_type_label or "",
        resource.cost_type_label or "",
        resource.employee_context or "",
        resource.contact or "",
        resource.address or "",
        resource.currency_code or "",
    )
    return any(normalized_search in value.casefold() for value in haystacks)

def matches_active(resource: Any, active_filter: str) -> bool:
    if active_filter == "all":
        return True
    if active_filter == "active":
        return bool(resource.is_active)
    if active_filter == "inactive":
        return not bool(resource.is_active)
    return True

def matches_category(resource: Any, category_filter: str) -> bool:
    if category_filter == "all":
        return True
    return resource.cost_type == category_filter

def normalize_active_filter(active_filter: str) -> str:
    normalized_value = (active_filter or "all").strip().lower()
    if normalized_value in {"all", "active", "inactive"}:
        return normalized_value
    return "all"

def normalize_category_filter(category_filter: str, category_options: Any) -> str:
    normalized_value = (category_filter or "all").strip().upper()
    available_values = {option.value.upper(): option.value for option in category_options}
    return available_values.get(normalized_value, "all")

def build_empty_state(
    *,
    all_resources: Any,
    filtered_resources: Any,
    search_text: str,
    active_filter: str,
    category_filter: str,
) -> str:
    if filtered_resources:
        return ""
    if not all_resources:
        return "No resources are available yet. Create the first PM resource to start planning capacity."
    if search_text or active_filter != "all" or category_filter != "all":
        return "No resources match the current filters."
    return "No resources are available yet."
