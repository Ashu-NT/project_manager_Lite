from __future__ import annotations

from typing import Any

def matches_cost_type(cost: Any, selected_cost_type: str) -> bool:
    if selected_cost_type == "all":
        return True
    return cost.cost_type == selected_cost_type

def matches_search(cost: Any, search_text: str) -> bool:
    if not search_text:
        return True
    normalized_search = search_text.casefold()
    haystacks = (
        cost.description or "",
        cost.task_name or "",
        cost.cost_type_label or "",
        cost.currency_code or "",
    )
    return any(normalized_search in value.casefold() for value in haystacks)

def build_empty_state(
    *,
    project_options: Any,
    all_costs: Any,
    filtered_costs: Any,
    selected_project_id: str,
    search_text: str,
    selected_cost_type: str,
) -> str:
    if not project_options:
        return "No projects are available yet. Create a project before managing financials."
    if not selected_project_id:
        return "Select a project to review financial controls."
    if filtered_costs:
        return ""
    if not all_costs:
        return "No cost items are available for the selected project."
    if search_text or selected_cost_type != "all":
        return "No cost items match the current filters."
    return "No cost items are available for the selected project."
