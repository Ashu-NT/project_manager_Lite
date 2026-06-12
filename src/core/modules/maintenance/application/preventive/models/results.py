"""Result and work-package DTOs for preventive generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MaintenancePreventiveGenerationResult:
    """Outcome of a single preventive plan generation attempt."""

    plan_id: str
    plan_code: str
    generation_target: str
    generated_work_request_id: str | None = None
    generated_work_order_id: str | None = None
    generated_task_ids: tuple[str, ...] = ()
    generated_step_ids: tuple[str, ...] = ()
    skipped_reason: str = ""


@dataclass(frozen=True)
class MaintenancePreventiveForecastRow:
    """A single row in a preventive schedule forecast."""

    instance_id: str
    due_at: datetime
    generation_window_opens_at: datetime
    instance_status: str
    planner_state: str
    generated_work_request_id: str | None = None
    generated_work_order_id: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class MaintenanceGeneratedWorkPackage:
    """IDs of tasks and steps created when populating a work order from a preventive plan."""

    generated_task_ids: list[str]
    generated_step_ids: list[str]


__all__ = [
    "MaintenanceGeneratedWorkPackage",
    "MaintenancePreventiveForecastRow",
    "MaintenancePreventiveGenerationResult",
]
