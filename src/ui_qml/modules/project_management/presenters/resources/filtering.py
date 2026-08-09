from __future__ import annotations

from typing import Any

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
    total: int,
    filtered_total: int,
    search_text: str,
    active_filter: str,
    category_filter: str,
) -> str:
    if filtered_total:
        return ""
    if not total:
        return "No resources are available yet. Create the first PM resource to start planning capacity."
    if search_text or active_filter != "all" or category_filter != "all":
        return "No resources match the current filters."
    return "No resources are available yet."
