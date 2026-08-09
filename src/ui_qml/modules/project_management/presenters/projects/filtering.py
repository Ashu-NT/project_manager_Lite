from __future__ import annotations

from typing import Any

def normalize_status_filter(status_filter: str, status_options: Any) -> str:
    normalized_value = (status_filter or "all").strip().lower()
    available_values = {option.value.lower(): option.value for option in status_options}
    return available_values.get(normalized_value, "all")

def build_empty_state(
    *,
    total: int,
    filtered_total: int,
    search_text: str,
    status_filter: str,
) -> str:
    if filtered_total:
        return ""
    if not total:
        return "No projects are available yet. Create the first project to start planning."
    if search_text or status_filter != "all":
        return "No projects match the current filters."
    return "No projects are available yet."
