"""Candidate and trigger evaluation DTOs for preventive generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.modules.maintenance.domain import MaintenanceSensor


@dataclass(frozen=True)
class MaintenanceTriggerEvaluation:
    """Result of evaluating whether a preventive trigger is due, blocked, or pending."""

    due: bool
    blocked: bool
    reason: str
    sensor: "MaintenanceSensor | None" = None


@dataclass(frozen=True)
class MaintenancePreventiveDueCandidate:
    """A preventive plan that has been evaluated for due-state."""

    plan_id: str
    plan_code: str
    plan_name: str
    due_state: str
    due_reason: str
    generation_target: str
    selected_plan_task_ids: tuple[str, ...] = ()
    blocked_plan_task_ids: tuple[str, ...] = ()


__all__ = ["MaintenancePreventiveDueCandidate", "MaintenanceTriggerEvaluation"]
