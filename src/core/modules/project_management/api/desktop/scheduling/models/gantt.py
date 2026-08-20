"""Typed, transport-neutral contracts for the disposable Gantt read model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class GanttTaskRowDto:
    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    code: str
    name: str
    description: str
    parent_task_id: str | None
    wbs_code: str
    sort_order: int
    depth: int
    is_summary: bool
    child_count: int
    ancestor_ids: tuple[str, ...]
    start_date: date | None
    finish_date: date | None
    start_day_ordinal: int | None
    finish_day_ordinal: int | None
    latest_start: date | None
    latest_finish: date | None
    duration_days: int | None
    remaining_duration_days: int | None
    status: str
    status_label: str
    percent_complete: float
    is_milestone: bool
    is_critical: bool
    is_infeasible: bool
    total_float_days: int | None
    has_canonical_schedule: bool
    constraint_type: str
    constraint_type_label: str
    constraint_date: date | None
    actual_start: date | None
    actual_finish: date | None
    actual_start_day_ordinal: int | None
    actual_finish_day_ordinal: int | None
    deadline: date | None
    late_by_days: int | None
    priority: int | None

    @property
    def id(self) -> str:
        """Compatibility alias for existing read-only scheduling presenters."""
        return self.task_id

    @property
    def actual_end(self) -> date | None:
        return self.actual_finish


@dataclass(frozen=True, slots=True)
class GanttDependencyEdgeDto:
    tenant_id: str
    organization_id: str
    project_id: str
    dependency_id: str
    predecessor_task_id: str
    predecessor_task_name: str
    successor_task_id: str
    successor_task_name: str
    dependency_type: str
    dependency_type_label: str
    lag_days: int

    @property
    def id(self) -> str:
        return self.dependency_id


@dataclass(frozen=True, slots=True)
class GanttBaselineTaskSnapshotDto:
    tenant_id: str
    organization_id: str
    project_id: str
    baseline_id: str
    task_id: str
    baseline_start: date | None
    baseline_finish: date | None
    baseline_duration_days: int
    baseline_is_milestone: bool
    baseline_start_day_ordinal: int | None
    baseline_finish_day_ordinal: int | None


@dataclass(frozen=True, slots=True)
class GanttNonWorkingIntervalDto:
    start_day_ordinal: int
    finish_day_ordinal: int


@dataclass(frozen=True, slots=True)
class GanttProjectionDto:
    tenant_id: str
    organization_id: str
    project_id: str
    schedule_authority: str
    selected_baseline_id: str | None
    project_start_day_ordinal: int | None
    project_finish_day_ordinal: int | None
    range_start_day_ordinal: int | None
    range_finish_day_ordinal: int | None
    calendar_shading_authoritative: bool
    non_working_intervals: tuple[GanttNonWorkingIntervalDto, ...]
    rows: tuple[GanttTaskRowDto, ...]
    dependency_edges: tuple[GanttDependencyEdgeDto, ...]
    baseline_snapshots: tuple[GanttBaselineTaskSnapshotDto, ...]


__all__ = [
    "GanttBaselineTaskSnapshotDto",
    "GanttDependencyEdgeDto",
    "GanttNonWorkingIntervalDto",
    "GanttProjectionDto",
    "GanttTaskRowDto",
]
