from __future__ import annotations

from datetime import date


def format_date(value: date | None) -> str:
    return value.isoformat() if value else "-"


def int_label(value: int | None) -> str:
    return "-" if value is None else str(int(value))


def shift_label(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{int(value):+d}d"


def calendar_label(
    calendar_options: tuple,
    selected_calendar_id: str,
) -> str:
    for option in calendar_options:
        if option.value == selected_calendar_id:
            return option.label
    return "Default Calendar"


def label_for_option(option_value: str, options: tuple) -> str:
    for option in options:
        if option.value == option_value:
            return option.label
    return option_value


def timeline_bounds(items: tuple) -> tuple[date | None, date | None]:
    starts = [item.start_date for item in items if item.start_date]
    finishes = [item.finish_date for item in items if item.finish_date]
    if not starts and not finishes:
        return None, None
    minimum = min(starts or finishes)
    maximum = max(finishes or starts)
    return minimum, maximum


def days_between(origin: date | None, target: date | None) -> int | None:
    if origin is None or target is None:
        return None
    return (target - origin).days


def constraint_label_for_activity(item) -> str:
    if item.actual_end:
        return "Actual finish locked"
    if item.actual_start:
        return "Actual start locked"
    if item.deadline:
        return "Finish no later than"
    if item.start_date:
        return "Planned start anchor"
    return "Open"


def build_schedule_empty_state(
    *,
    resolved_project_id: str,
    schedule_items,
) -> str:
    if not resolved_project_id:
        return "Select a project to review the current schedule."
    if schedule_items:
        return ""
    return "No scheduled activities are available for the selected project."


__all__ = [
    "format_date",
    "int_label",
    "shift_label",
    "calendar_label",
    "label_for_option",
    "timeline_bounds",
    "days_between",
    "constraint_label_for_activity",
    "build_schedule_empty_state",
]
