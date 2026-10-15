"""Calendar calendar resolution inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ResolveContextCommand:
    target_date: date | str
    site_id: str | None = None
    department_id: str | None = None
    employee_id: str | None = None
    project_id: str | None = None
    resource_id: str | None = None
    worker_type: str | None = None
    assigned_hours: float = 0.0


@dataclass(frozen=True)
class ResolveEffectiveCalendarCommand:
    site_id: str | None = None
    department_id: str | None = None
    employee_id: str | None = None
    project_id: str | None = None
    resource_id: str | None = None
    worker_type: str | None = None
    at_date: date | str | None = None


@dataclass(frozen=True)
class ResolveCalendarRangeCommand:
    start_date: date | str
    end_date: date | str
    site_id: str | None = None
    department_id: str | None = None
    employee_id: str | None = None
    project_id: str | None = None
    resource_id: str | None = None
    worker_type: str | None = None
    assigned_hours_by_date: dict[date, float] | None = None
