from __future__ import annotations


def matches_search(search_text: str, *values: str) -> bool:
    normalized = search_text.casefold()
    return any(normalized in str(value or "").casefold() for value in values)


def normalize_filter(filter_value: str, options) -> str:
    normalized_input = (filter_value or "").strip().casefold()
    for option in options:
        if str(option.value or "").casefold() == normalized_input:
            return option.value
    return options[0].value if options else "all"
