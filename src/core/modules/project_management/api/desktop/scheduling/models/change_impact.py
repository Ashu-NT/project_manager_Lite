from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SchedulingChangeImpactAffectedTaskDto:
    task_id: str
    task_name: str
    start_shift_days: int
    finish_shift_days: int
    is_critical: bool


@dataclass(frozen=True)
class SchedulingChangeImpactDto:
    task_id: str
    affected_count: int
    max_project_finish_shift_days: int
    requires_approval: bool
    newly_critical_count: int
    no_longer_critical_count: int
    affected_tasks: tuple[SchedulingChangeImpactAffectedTaskDto, ...]


@dataclass(frozen=True)
class ScheduleImpactAffectedTaskDto:
    task_id: str
    task_name: str
    original_start: date | None
    original_finish: date | None
    proposed_start: date | None
    proposed_finish: date | None
    start_shift_days: int
    finish_shift_days: int
    is_critical: bool


@dataclass(frozen=True)
class ScheduleImpactReportDto:
    task_id: str
    project_id: str
    is_available: bool
    simulated_delay_days: int
    affected_count: int
    max_project_finish_shift_days: int
    requires_approval: bool
    affected_tasks: tuple[ScheduleImpactAffectedTaskDto, ...]
    newly_critical_task_ids: tuple[str, ...]
    no_longer_critical_task_ids: tuple[str, ...]


__all__ = [
    "ScheduleImpactAffectedTaskDto",
    "ScheduleImpactReportDto",
    "SchedulingChangeImpactAffectedTaskDto",
    "SchedulingChangeImpactDto",
]
