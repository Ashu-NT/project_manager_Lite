"""Calendar working days inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WorkingDaysCommand:
    start_date: date | str
    end_date: date | str = ""
    working_days: int = 0
    project_id: str | None = None
    resource_id: str | None = None
