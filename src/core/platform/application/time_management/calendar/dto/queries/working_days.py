"""Calendar working days inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WorkingDayCalculationCommand:
    start_date: date
    working_days: int
