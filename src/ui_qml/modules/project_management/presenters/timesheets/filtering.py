from __future__ import annotations


def normalize_filter(value: str, options, *, default_value: str) -> str:
    normalized_value = (value or default_value).strip().lower()
    available_values = {
        str(option.value or "").strip().lower(): option.value
        for option in options
    }
    return available_values.get(normalized_value, default_value)
