"""Transport-neutral application response DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SchedulingBaselineResponse:
    id: str
    project_id: str
    name: str
    created_at: date
    status: str
    version: int
    submitted_by: str | None
    submitted_at: date | None
    approved_by: str | None
    approved_at: date | None
    notes: str
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
    planned_cost_delta: Decimal


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
    cost_variance: Decimal
    created_at: date | None

