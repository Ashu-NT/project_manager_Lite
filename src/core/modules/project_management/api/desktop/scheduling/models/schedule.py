from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SchedulingProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class SchedulingTaskDto:
    id: str
    project_id: str
    name: str
    description: str
    status: str
    status_label: str
    start_date: date | None
    finish_date: date | None
    latest_start: date | None
    latest_finish: date | None
    duration_days: int | None
    remaining_duration_days: int | None
    total_float_days: int | None
    is_critical: bool
    deadline: date | None
    late_by_days: int | None
    percent_complete: float
    actual_start: date | None
    actual_end: date | None
    priority: int | None


__all__ = ["SchedulingProjectOptionDescriptor", "SchedulingTaskDto"]
