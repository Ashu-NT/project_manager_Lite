from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SchedulingBaselineOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class SchedulingBaselineRowDto:
    id: str
    name: str
    created_at: date | None
    created_at_label: str
    approved_by_label: str
    variance_state_label: str
    status: str
    status_label: str
    can_submit: bool
    can_approve: bool
    can_reject: bool


@dataclass(frozen=True)
class SchedulingBaselineComparisonRowDto:
    task_id: str
    task_name: str
    change_type: str
    baseline_a_start: date | None
    baseline_a_finish: date | None
    baseline_b_start: date | None
    baseline_b_finish: date | None
    start_shift_days: int | None
    finish_shift_days: int | None
    duration_delta_days: int | None
    planned_cost_delta: float


@dataclass(frozen=True)
class SchedulingBaselineVarianceRowDto:
    id: str
    project_id: str
    new_baseline_id: str
    superseded_baseline_id: str
    task_id: str
    task_name: str
    start_variance_days: int
    finish_variance_days: int
    cost_variance: float
    created_at: date | None


__all__ = [
    "SchedulingBaselineComparisonRowDto",
    "SchedulingBaselineOptionDescriptor",
    "SchedulingBaselineRowDto",
    "SchedulingBaselineVarianceRowDto",
]
