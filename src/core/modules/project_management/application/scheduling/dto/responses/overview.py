"""Neutral current-schedule responses; display labels remain in desktop."""

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.scheduling.dto.responses.change_impact import (
    ActualVarianceDto,
    DownstreamExposureDto,
)


@dataclass(frozen=True)
class ScheduleDriverResponseDto:
    kind: str
    value: str
    detail: str


@dataclass(frozen=True)
class ScheduleConflictResponseDto:
    task_id: str
    task_name: str
    constraint_type: str
    constraint_date: date
    dependency_required_date: date
    direction: str
    difference_working_days: int


@dataclass(frozen=True)
class TaskScheduleOverviewResponseDto:
    task_id: str
    is_available: bool
    unavailable_reason: str
    current_start: date | None
    current_finish: date | None
    is_critical: bool
    is_infeasible: bool
    total_float_days: int | None
    free_float_days: int | None
    baseline_finish: date | None
    schedule_variance_days: int | None
    drivers: tuple[ScheduleDriverResponseDto, ...]
    dependency_conflicts: tuple[ScheduleConflictResponseDto, ...]
    actual_variances: tuple[ActualVarianceDto, ...]
    downstream: DownstreamExposureDto
