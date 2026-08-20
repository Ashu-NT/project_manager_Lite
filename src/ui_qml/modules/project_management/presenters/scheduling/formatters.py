from __future__ import annotations

from datetime import date
from typing import Any

def format_date(value: date | None) -> str:
    return value.isoformat() if value else "-"

def int_label(value: int | None) -> str:
    return "-" if value is None else str(int(value))

def shift_label(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{int(value):+d}d"

def label_for_option(option_value: str, options: Any) -> str:
    for option in options:
        if option.value == option_value:
            return option.label
    return option_value

def constraint_label_for_activity(item: Any) -> str:
    if item.actual_end:
        return "Actual finish locked"
    if item.actual_start:
        return "Actual start locked"
    # A real Task.constraint_type takes precedence over the deadline --
    # Deadline is a distinct concept and must never be labeled as FNLT
    # (see constraint_presentation.py's module docstring).
    if getattr(item, "constraint_type", ""):
        return item.constraint_type_label
    if item.deadline:
        return "Deadline"
    if item.start_date:
        return "Planned start anchor"
    return "Open"

__all__ = [
    "format_date",
    "int_label",
    "shift_label",
    "label_for_option",
    "constraint_label_for_activity",
]
