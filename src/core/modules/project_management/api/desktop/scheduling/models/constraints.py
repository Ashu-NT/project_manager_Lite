from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SchedulingConstraintViolationDto:
    task_id: str
    task_name: str
    constraint_type: str
    constraint_type_label: str
    constraint_date: date | None
    constraint_date_label: str
    computed_date: date | None
    computed_date_label: str
    overrun_working_days: int
    message: str
    severity: str
    severity_label: str


__all__ = ["SchedulingConstraintViolationDto"]
