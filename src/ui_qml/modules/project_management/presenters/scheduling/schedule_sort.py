from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

_ALLOWED_SORT_KEYS = {
    "wbs",
    "taskName",
    "start",
    "finish",
    "duration",
    "remainingDuration",
    "float",
    "critical",
    "constraint",
    "progress",
    "status",
}


class ScheduleSortDirection(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


@dataclass(frozen=True, slots=True)
class ScheduleSort:
    key: str
    direction: ScheduleSortDirection = ScheduleSortDirection.ASCENDING


def normalize_schedule_sort(*, key: object, direction: object) -> ScheduleSort:
    normalized_key = str(key or "").strip()
    if normalized_key not in _ALLOWED_SORT_KEYS:
        return ScheduleSort(key="schedule")
    normalized_direction = str(
        getattr(direction, "value", direction) or ""
    ).strip().lower()
    resolved_direction = (
        ScheduleSortDirection.DESCENDING
        if normalized_direction in {"desc", "descending", "1"}
        else ScheduleSortDirection.ASCENDING
    )
    return ScheduleSort(key=normalized_key, direction=resolved_direction)

__all__ = ["ScheduleSort", "normalize_schedule_sort"]
