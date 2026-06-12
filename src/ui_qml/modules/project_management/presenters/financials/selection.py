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

def normalize_cost_type_filter(
    selected_cost_type: str,
    cost_type_options: Any,
) -> str:
    normalized_value = (selected_cost_type or "all").strip().upper()
    available = {option.value.upper(): option.value for option in cost_type_options}
    return available.get(normalized_value, "all")

def resolve_selected_cost_id(
    selected_cost_id: str | None,
    filtered_costs: Any,
) -> str:
    normalized_value = (selected_cost_id or "").strip()
    if normalized_value and any(cost.id == normalized_value for cost in filtered_costs):
        return normalized_value
    if filtered_costs:
        return filtered_costs[0].id
    return ""
