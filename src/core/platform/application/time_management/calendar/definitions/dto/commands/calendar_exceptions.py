"""Calendar calendar exceptions inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class ExceptionCreateCommand:
    calendar_id: str
    exception_date: date | str
    exception_type: str
    name: str
    impact_type: str
    scope_type: str | None = None
    scope_id: str | None = None
    description: str = ""
    start_time: time | str | None = None
    end_time: time | str | None = None
    hours_override: float | None = None
    priority: int = 0
    approval_status: str = "APPROVED"


@dataclass(frozen=True)
class ExceptionUpdateCommand:
    exception_id: str
    name: str = ""
    description: str = ""
    exception_type: str = ""
    impact_type: str = ""
    hours_override: float | None = None
    priority: int | None = None
    approval_status: str = ""
    approved_by: str = ""
    start_time: time | None = None
    end_time: time | None = None
