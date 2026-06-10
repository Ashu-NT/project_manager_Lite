from __future__ import annotations

from .formatters import format_date


def matches_schedule_filters(
    item,
    *,
    status_filter: str,
    search_text: str,
    show_critical_only: bool,
    show_delayed_only: bool,
) -> bool:
    if status_filter != "all" and str(item.status or "").strip().upper() != status_filter.upper():
        return False
    if show_critical_only and not bool(item.is_critical):
        return False
    if show_delayed_only and not ((item.late_by_days or 0) > 0):
        return False
    if not search_text:
        return True
    normalized_search = search_text.casefold()
    haystacks = (
        item.id,
        item.name,
        item.description or "",
        item.status_label or "",
        format_date(item.start_date),
        format_date(item.finish_date),
    )
    return any(normalized_search in str(value or "").casefold() for value in haystacks)


__all__ = ["matches_schedule_filters"]
