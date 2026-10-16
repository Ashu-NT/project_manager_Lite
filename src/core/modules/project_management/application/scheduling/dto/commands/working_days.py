from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.platform.application.time_management.calendar.capacity.dto.queries.working_days import (
    WorkingDaysCommand,
)


@dataclass(frozen=True, init=False)
class SchedulingWorkingDayCalculationCommand(WorkingDaysCommand):
    """Date-typed scheduling input accepted unchanged by the calendar resolver."""

    start_date: date

    def __init__(self, start_date: date, working_days: int) -> None:
        super().__init__(start_date=start_date, working_days=working_days)
