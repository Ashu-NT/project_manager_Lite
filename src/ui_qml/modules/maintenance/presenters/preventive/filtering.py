from __future__ import annotations


def matches_search(search_text: str, *values: str) -> bool:
    if not search_text:
        return True
    normalized = search_text.casefold()
    return any(normalized in str(value or "").casefold() for value in values)


def normalize_filter(filter_value: str, options: list[dict[str, str]]) -> str:
    normalized_input = (filter_value or "").strip().casefold()
    for opt in options:
        if str(opt.get("value", "")).casefold() == normalized_input:
            return str(opt["value"])
    return str(options[0]["value"]) if options else "all"


def to_active_only(filter_value: str) -> bool | None:
    if filter_value == "active":
        return True
    if filter_value == "inactive":
        return False
    return None
