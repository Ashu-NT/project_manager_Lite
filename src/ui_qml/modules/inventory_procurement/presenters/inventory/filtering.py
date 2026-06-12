from __future__ import annotations


def matches_active(is_active: bool, active_filter: str) -> bool:
    if active_filter == "all":
        return True
    if active_filter == "active":
        return bool(is_active)
    if active_filter == "inactive":
        return not bool(is_active)
    return True


def matches_site(site_id: str, site_filter: str) -> bool:
    return site_filter == "all" or site_id == site_filter


def matches_storeroom_filter(storeroom_id: str, storeroom_filter: str) -> bool:
    return storeroom_filter == "all" or storeroom_id == storeroom_filter


def matches_item(stock_item_id: str, item_filter: str) -> bool:
    return item_filter == "all" or stock_item_id == item_filter


def matches_transaction_type(transaction_type: str, filter_value: str) -> bool:
    return filter_value == "all" or transaction_type == filter_value


def matches_search(search_text: str, *values: str) -> bool:
    if not search_text:
        return True
    normalized = search_text.casefold()
    return any(normalized in str(value or "").casefold() for value in values)


def normalize_filter(filter_value: str, options) -> str:
    normalized_input = (filter_value or "").strip().casefold()
    for option in options:
        if str(option.value or "").casefold() == normalized_input:
            return option.value
    return options[0].value if options else "all"


def normalize_active_filter(active_filter: str) -> str:
    normalized_value = (active_filter or "all").strip().lower()
    if normalized_value in {"all", "active", "inactive"}:
        return normalized_value
    return "all"
