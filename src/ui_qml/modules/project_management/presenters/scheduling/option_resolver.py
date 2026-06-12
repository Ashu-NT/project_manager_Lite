from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingSelectorOptionViewModel,
)

def resolve_project_id(
    project_id: str | None,
    project_options: tuple[SchedulingSelectorOptionViewModel, ...],
) -> str:
    normalized_id = (project_id or "").strip()
    option_values = {option.value for option in project_options}
    if normalized_id and normalized_id in option_values:
        return normalized_id
    if project_options:
        return project_options[0].value
    return ""

def resolve_selected_option(
    selected_value: str | None,
    options: tuple[SchedulingSelectorOptionViewModel, ...],
    *,
    default_value: str,
) -> str:
    normalized_value = (selected_value or "").strip()
    if normalized_value and any(option.value == normalized_value for option in options):
        return normalized_value
    if options:
        return options[0].value
    return default_value

def resolve_baseline_ids(
    *,
    baseline_options: tuple[SchedulingSelectorOptionViewModel, ...],
    selected_baseline_a_id: str | None,
    selected_baseline_b_id: str | None,
) -> tuple[str, str]:
    option_values = [option.value for option in baseline_options]
    if not option_values:
        return "", ""
    normalized_a = (selected_baseline_a_id or "").strip()
    normalized_b = (selected_baseline_b_id or "").strip()
    if normalized_a not in option_values:
        normalized_a = option_values[1] if len(option_values) > 1 else option_values[0]
    if normalized_b not in option_values:
        normalized_b = option_values[0]
    return normalized_a, normalized_b

def build_status_options(
    schedule_items: Any,
) -> tuple[SchedulingSelectorOptionViewModel, ...]:
    labels = sorted(
        {
            str(item.status or "").strip()
            for item in schedule_items
            if str(item.status or "").strip()
        }
    )
    return (
        SchedulingSelectorOptionViewModel(value="all", label="All statuses"),
        *(
            SchedulingSelectorOptionViewModel(
                value=value,
                label=value.replace("_", " ").title(),
            )
            for value in labels
        ),
    )

def resolve_selected_activity_id(
    selected_activity_id: str | None,
    *,
    filtered_schedule: Any,
    paged_schedule: Any,
) -> str:
    normalized_id = (selected_activity_id or "").strip()
    filtered_ids = {item.id for item in filtered_schedule}
    if normalized_id and normalized_id in filtered_ids:
        return normalized_id
    if paged_schedule:
        return paged_schedule[0].id
    return ""

__all__ = [
    "resolve_project_id",
    "resolve_selected_option",
    "resolve_baseline_ids",
    "build_status_options",
    "resolve_selected_activity_id",
]
