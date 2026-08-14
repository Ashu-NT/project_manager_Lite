from __future__ import annotations


def normalize_filter(value: str, options, *, default_value: str) -> str:
    normalized_value = (value or default_value).strip().lower()
    available_values = {
        str(option.value or "").strip().lower(): option.value
        for option in options
    }
    return available_values.get(normalized_value, default_value)


def build_empty_state(
    *,
    intake_total: int,
    intake_status_filter: str,
    templates,
    scenarios,
) -> str:
    if intake_total > 0:
        return ""
    if intake_status_filter != "all":
        return "No intake items match the current status filter."
    if not templates:
        return "No scoring templates or intake items are available yet. Start by creating the first scoring template."
    if not scenarios:
        return "No portfolio scenarios are available yet. Create intake items and save the first scenario."
    return "No portfolio planning data is available yet."
