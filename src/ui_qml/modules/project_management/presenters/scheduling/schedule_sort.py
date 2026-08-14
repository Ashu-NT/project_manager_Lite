from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from src.core.modules.project_management.contracts.reads import ReadSort

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


def normalize_schedule_sort(*, key: object, direction: object) -> ReadSort:
    return ReadSort.normalize(
        key=key,
        direction=direction,
        allowed_keys=_SORT_ACCESSORS.keys(),
        default_key="schedule",
    )


def sort_schedule_items(items: Iterable[Any], *, sort: ReadSort) -> tuple[Any, ...]:
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


__all__ = ["normalize_schedule_sort", "sort_schedule_items"]
