from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class EvmSeriesPoint:
    period_end: date
    PV: float
    EV: float
    AC: float
    BAC: float
    CPI: float
    SPI: float


@dataclass
class EarnedValueMetrics:
    as_of: date
    baseline_id: str

    BAC: float
    PV: float
    EV: float
    AC: float

    CPI: Optional[float]
    SPI: Optional[float]
    EAC: Optional[float]
    ETC: Optional[float]
    VAC: Optional[float]
    TCPI_to_BAC: Optional[float] = None
    TCPI_to_EAC: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class LaborAssignmentRow:
    assignment_id: str
    task_id: str
    task_name: str
    hours: float
    hourly_rate: float
    currency_code: Optional[str]
    cost: float


@dataclass
class LaborResourceRow:
    resource_id: str
    resource_name: str
    total_hours: float
    hourly_rate: float
    currency_code: Optional[str]
    total_cost: float
    assignments: List[LaborAssignmentRow]


@dataclass
class LaborPlanActualRow:
    resource_id: str
    resource_name: str
    planned_hours: float
    planned_hourly_rate: float
    planned_currency_code: Optional[str]
    planned_cost: float
    actual_hours: float
    actual_currency_code: Optional[str]
    actual_cost: float
    variance_cost: float


@dataclass
class GanttTaskBar:
    task_id: str
    name: str
    start: Optional[date]
    end: Optional[date]
    is_critical: bool
    percent_complete: float
    status: str


@dataclass
class ProjectKPI:
    project_id: str
    name: str
    start_date: Optional[date]
    end_date: Optional[date]
    duration_working_days: Optional[int]
    tasks_total: int
    tasks_completed: int
    tasks_in_progress: int
    task_blocked: int
    tasks_not_started: int
    critical_tasks: int
    late_tasks: int
    total_planned_cost: float
    total_actual_cost: float
    cost_variance: float
    total_committed_cost: float
    committment_variance: float


@dataclass
class ResourceLoadRow:
    resource_id: str
    resource_name: str
    total_allocation_percent: float
    tasks_count: int


@dataclass
class TaskVarianceRow:
    task_id: str
    task_name: str
    baseline_start: date | None
    baseline_finish: date | None
    current_start: date | None
    current_finish: date | None
    start_variance_days: int | None
    finish_variance_days: int | None
    is_critical: bool


@dataclass
class BaselineComparisonRow:
    task_id: str
    task_name: str
    baseline_a_start: date | None
    baseline_a_finish: date | None
    baseline_a_duration_days: int | None
    baseline_a_planned_cost: float | None
    baseline_b_start: date | None
    baseline_b_finish: date | None
    baseline_b_duration_days: int | None
    baseline_b_planned_cost: float | None
    start_shift_days: int | None
    finish_shift_days: int | None
    duration_delta_days: int | None
    planned_cost_delta: float
    change_type: str


@dataclass
class BaselineComparisonResult:
    project_id: str
    baseline_a_id: str
    baseline_a_name: str
    baseline_a_created_at: date | None
    baseline_b_id: str
    baseline_b_name: str
    baseline_b_created_at: date | None
    total_tasks_compared: int
    changed_tasks: int
    added_tasks: int
    removed_tasks: int
    unchanged_tasks: int
    rows: list[BaselineComparisonRow]


@dataclass
class CostBreakdownRow:
    cost_type: str
    currency: str
    planned: float
    actual: float


