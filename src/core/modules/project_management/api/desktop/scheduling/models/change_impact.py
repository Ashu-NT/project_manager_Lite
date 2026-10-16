from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.scheduling.dto.responses.change_impact import (
    ActualVarianceDto,
    DownstreamExposureDto,
)


@dataclass(frozen=True)
class ScheduleDriverDto:
    kind: str
    label: str
    detail: str


@dataclass(frozen=True)
class ScheduleConflictDto:
    task_id: str
    task_name: str
    constraint_type: str
    constraint_type_label: str
    constraint_date: date
    dependency_required_date: date
    direction: str
    difference_working_days: int






@dataclass(frozen=True)
class TaskScheduleImpactOverviewDesktopDto:
    """Task Detail -> Schedule Impact's always-visible current-state facts.
    Deliberately a different shape from ScheduleImpactReportDto: this is
    "what is true now," not "what would a hypothetical change produce"."""

    task_id: str
    is_available: bool
    unavailable_reason: str
    current_start_label: str
    current_finish_label: str
    is_critical: bool
    is_infeasible: bool
    total_float_days: int | None
    free_float_days: int | None
    baseline_finish_label: str
    schedule_variance_days: int | None
    drivers: tuple[ScheduleDriverDto, ...]
    conflicts: tuple[ScheduleConflictDto, ...]
    actual_variances: tuple[ActualVarianceDto, ...]
    downstream: DownstreamExposureDto


__all__ = ['ScheduleConflictDto', 'ScheduleDriverDto', 'TaskScheduleImpactOverviewDesktopDto']
