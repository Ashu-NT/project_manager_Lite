from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .formatters import constraint_label_for_activity


_SORT_ACCESSORS: dict[str, Callable[[Any], object]] = {
    "wbs": lambda item: str(item.wbs_code or "").casefold(),
    "taskName": lambda item: str(item.name or "").casefold(),
    "start": lambda item: item.start_date,
    "finish": lambda item: item.finish_date,
    "duration": lambda item: item.duration_days,
    "remainingDuration": lambda item: item.remaining_duration_days,
    "float": lambda item: item.total_float_days,
    "critical": lambda item: bool(item.is_critical),
    "constraint": lambda item: constraint_label_for_activity(item).casefold(),
    "progress": lambda item: float(item.percent_complete or 0.0),
    "status": lambda item: str(item.status_label or "").casefold(),
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
    if normalized_key not in _SORT_ACCESSORS:
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


def sort_schedule_items(items: Iterable[Any], *, sort: ScheduleSort) -> tuple[Any, ...]:
    rows = tuple(items)
    if sort.key == "schedule":
        return rows

    accessor = _SORT_ACCESSORS[sort.key]
    populated = [item for item in rows if accessor(item) is not None]
    missing = [item for item in rows if accessor(item) is None]
    populated.sort(key=lambda item: str(item.id))
    populated.sort(
        key=accessor,
        reverse=sort.direction.value == "desc",
    )
    missing.sort(key=lambda item: str(item.id))
    return (*populated, *missing)


__all__ = ["ScheduleSort", "normalize_schedule_sort", "sort_schedule_items"]
