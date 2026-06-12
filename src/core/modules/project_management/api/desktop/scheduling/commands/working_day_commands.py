from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SchedulingWorkingDayCalculationCommand:
    start_date: date
    working_days: int


__all__ = ["SchedulingWorkingDayCalculationCommand"]
