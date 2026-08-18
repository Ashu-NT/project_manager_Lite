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
    project_name_filter: str = "",
    client_name_filter: str = "",
    site_filter: str = "all",
    department_filter: str = "all",
    manager_filter: str = "all",
    start_date_from: str = "",
    start_date_to: str = "",
    end_date_from: str = "",
    end_date_to: str = "",
) -> str:
    if filtered_total:
        return ""
    if not total:
        return "No projects are available yet. Create the first project to start planning."
    any_filter_active = (
        bool(search_text)
        or status_filter != "all"
        or bool(project_name_filter)
        or bool(client_name_filter)
        or site_filter != "all"
        or department_filter != "all"
        or manager_filter != "all"
        or bool(start_date_from)
        or bool(start_date_to)
        or bool(end_date_from)
        or bool(end_date_to)
    )
    if any_filter_active:
        return "No projects match the current filters."
    return "No projects are available yet."
