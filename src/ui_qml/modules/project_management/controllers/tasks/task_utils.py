from __future__ import annotations


def coerce_non_negative_int(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def normalize_task_view_state(state: dict[str, object]) -> dict[str, object]:
    return {
        "query": str(state.get("query", "") or "").strip(),
        "status": coerce_non_negative_int(state.get("status", 0)),
        "priority": coerce_non_negative_int(state.get("priority", 0)),
        "schedule": coerce_non_negative_int(state.get("schedule", 0)),
    }


def index_for_option_value(
    options: list[dict[str, str]], target_value: str
) -> int:
    target = str(target_value or "")
    for i, option in enumerate(options):
        if str(option.get("value", "") or "") == target:
            return i
    return 0


def option_value_for_index(
    options: list[dict[str, str]],
    index_value: object,
    *,
    default_value: str,
) -> str:
    idx = coerce_non_negative_int(index_value)
    if 0 <= idx < len(options):
        return str(options[idx].get("value", "") or default_value)
    if options:
        return str(options[0].get("value", "") or default_value)
    return default_value


__all__ = [
    "coerce_non_negative_int",
    "index_for_option_value",
    "normalize_task_view_state",
    "option_value_for_index",
]
