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
    is_milestone: bool = False


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
    critical_path_changed: bool = False
    conflict_count: int = 0
    blocked_by_deadline: bool = False
    blocked_reason: str = ""


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
class ActualVarianceDto:
    task_id: str
    task_name: str
    direction: str
    actual_date: date
    dependency_required_date: date
    difference_working_days: int


@dataclass(frozen=True)
class DownstreamExposureDto:
    direct_successor_count: int
    downstream_task_count: int
    downstream_milestone_count: int
    critical_downstream_count: int


@dataclass(frozen=True)
class TaskScheduleImpactOverviewDesktopDto:
    """Task Detail -> Schedule Impact's always-visible current-state
    facts. Deliberately a different shape from ScheduleImpactReportDto --
    this is "what is true now," not "what would a hypothetical change
    produce" (see docs/pm_modernization/R4_4_TASK_DEPENDENCY_IMPLEMENTATION_SUMMARY.md,
    "Task Detail -> Schedule Impact")."""

    task_id: str
    is_available: bool
    unavailable_reason: str
    current_start_label: str
    current_finish_label: str
    is_critical: bool
    total_float_days: int | None
    free_float_days: int | None
    baseline_finish_label: str
    schedule_variance_days: int | None
    drivers: tuple[ScheduleDriverDto, ...]
    conflicts: tuple[ScheduleConflictDto, ...]
    actual_variances: tuple[ActualVarianceDto, ...]
    downstream: DownstreamExposureDto


__all__ = [
    "ActualVarianceDto",
    "DownstreamExposureDto",
    "ScheduleConflictDto",
    "ScheduleDriverDto",
    "ScheduleImpactAffectedTaskDto",
    "ScheduleImpactReportDto",
    "SchedulingChangeImpactAffectedTaskDto",
    "SchedulingChangeImpactDto",
    "TaskScheduleImpactOverviewDesktopDto",
]
