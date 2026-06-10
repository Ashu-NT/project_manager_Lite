from __future__ import annotations


def resolve_selected_id(selected_id: str | None, options) -> str:
    normalized_id = (selected_id or "").strip()
    available_values = [str(option.value or "") for option in options]
    if normalized_id and normalized_id in available_values:
        return normalized_id
    return available_values[0] if available_values else ""
