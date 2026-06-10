from __future__ import annotations


def matches_active(is_active: bool, active_filter: str) -> bool:
    if active_filter == "all":
        return True
    if active_filter == "active":
        return bool(is_active)
    if active_filter == "inactive":
        return not bool(is_active)
    return True


def matches_category_type(category, category_type_filter: str) -> bool:
    if category_type_filter == "all":
        return True
    return category.category_type == category_type_filter


def matches_usage(category, usage_filter: str) -> bool:
    if usage_filter == "all":
        return True
    if usage_filter == "equipment":
        return bool(category.is_equipment)
    if usage_filter == "projects":
        return bool(category.supports_project_usage)
    if usage_filter == "maintenance":
        return bool(category.supports_maintenance_usage)
    return True


def matches_category_search(category, search_text: str) -> bool:
    if not search_text:
        return True
    normalized = search_text.casefold()
    haystacks = (
        category.category_code or "",
        category.name or "",
        category.description or "",
        category.category_type_label or "",
    )
    return any(normalized in value.casefold() for value in haystacks)


def matches_item_category(item, category_filter: str) -> bool:
    if category_filter == "all":
        return True
    return item.category_code == category_filter


def matches_item_usage(item, usage_filter: str, categories_by_code) -> bool:
    if usage_filter == "all":
        return True
    category = categories_by_code.get(item.category_code)
    if category is None:
        return False
    return matches_usage(category, usage_filter)


def matches_item_search(item, search_text: str) -> bool:
    if not search_text:
        return True
    normalized = search_text.casefold()
    haystacks = (
        item.item_code or "",
        item.name or "",
        item.description or "",
        item.category_label or "",
        item.preferred_party_label or "",
        item.status_label or "",
        item.commodity_code or "",
    )
    return any(normalized in value.casefold() for value in haystacks)


def normalize_active_filter(active_filter: str) -> str:
    normalized_value = (active_filter or "all").strip().lower()
    if normalized_value in {"all", "active", "inactive"}:
        return normalized_value
    return "all"


def normalize_usage_filter(usage_filter: str) -> str:
    normalized_value = (usage_filter or "all").strip().lower()
    if normalized_value in {"all", "equipment", "projects", "maintenance"}:
        return normalized_value
    return "all"


def normalize_option_filter(filter_value: str, options) -> str:
    normalized_value = (filter_value or "all").strip().upper()
    available_values = {option.value.upper(): option.value for option in options}
    return available_values.get(normalized_value, "all")
