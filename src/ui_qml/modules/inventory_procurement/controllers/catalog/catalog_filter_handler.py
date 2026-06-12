from __future__ import annotations


def set_search_text(ctrl, search_text: str) -> None:
    normalized = (search_text or "").strip()
    if normalized == ctrl._search_text:
        return
    ctrl._set_search_text(normalized)
    ctrl.refresh()


def set_active_filter(ctrl, active_filter: str) -> None:
    normalized = (active_filter or "").strip().lower() or "all"
    if normalized == ctrl._selected_active_filter:
        return
    ctrl._set_selected_active_filter(normalized)
    ctrl.refresh()


def set_usage_filter(ctrl, usage_filter: str) -> None:
    normalized = (usage_filter or "").strip().lower() or "all"
    if normalized == ctrl._selected_usage_filter:
        return
    ctrl._set_selected_usage_filter(normalized)
    ctrl.refresh()


def set_category_type_filter(ctrl, category_type: str) -> None:
    normalized = (category_type or "").strip() or "all"
    if normalized == ctrl._selected_category_type_filter:
        return
    ctrl._set_selected_category_type_filter(normalized)
    ctrl.refresh()


def set_category_filter(ctrl, category_code: str) -> None:
    normalized = (category_code or "").strip() or "all"
    if normalized == ctrl._selected_category_filter:
        return
    ctrl._set_selected_category_filter(normalized)
    ctrl.refresh()


def clear_filters(ctrl) -> None:
    ctrl._set_selected_active_filter("all")
    ctrl._set_selected_usage_filter("all")
    ctrl._set_selected_category_type_filter("all")
    ctrl._set_selected_category_filter("all")
    ctrl._set_search_text("")
    ctrl.refresh()
