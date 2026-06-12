from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TimesheetPeriodSummaryDesktopDto:
    period_id: str
    resource_id: str
    resource_name: str
    period_start: date
    period_start_label: str
    period_end_label: str
    status: str
    status_label: str
    submitted_by_username: str
    submitted_at_label: str
    decided_by_username: str
    decided_at_label: str
    decision_note: str
    entry_count: int
    total_hours: float
    total_hours_label: str
    project_names: tuple[str, ...]


__all__ = ["TimesheetPeriodSummaryDesktopDto"]
