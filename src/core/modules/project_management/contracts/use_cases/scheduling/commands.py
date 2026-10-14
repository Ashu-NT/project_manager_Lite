"""Scheduling use-case commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.enums import DependencyType


@dataclass(frozen=True)
class SchedulingBaselineCreateCommand:
    project_id: str
    name: str = "Baseline"


@dataclass(frozen=True)
class SchedulingBaselineSubmitCommand:
    baseline_id: str
    submitted_by: str = "system"
    notes: str = ""


@dataclass(frozen=True)
class SchedulingBaselineApproveCommand:
    baseline_id: str
    approved_by: str = "system"
    notes: str = ""


@dataclass(frozen=True)
class SchedulingBaselineRejectCommand:
    baseline_id: str
    notes: str = ""


@dataclass(frozen=True)
class SchedulingDependencyCreateCommand:
    task_id: str
    related_activity_id: str
    relationship_direction: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    lag_days: int = 0


@dataclass(frozen=True)
class SchedulingDependencyUpdateCommand:
    dependency_id: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    lag_days: int = 0


@dataclass(frozen=True)
class SchedulingWorkingDayCalculationCommand:
    start_date: date
    working_days: int


__all__ = [
    "SchedulingBaselineApproveCommand",
    "SchedulingBaselineCreateCommand",
    "SchedulingBaselineRejectCommand",
    "SchedulingBaselineSubmitCommand",
    "SchedulingDependencyCreateCommand",
    "SchedulingDependencyUpdateCommand",
    "SchedulingWorkingDayCalculationCommand",
]
