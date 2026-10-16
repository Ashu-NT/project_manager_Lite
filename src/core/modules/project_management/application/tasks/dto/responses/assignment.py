"""Neutral assignment command/query response, without display formatting."""

from dataclasses import dataclass
from decimal import Decimal

from src.core.modules.project_management.application.resources.capacity.task_assignment_capacity_service import (
    TaskAssignmentCapacityFact,
)


@dataclass(frozen=True)
class TaskAssignmentResponseDto:
    id: str
    task_id: str
    resource_id: str
    resource_name: str
    allocation_percent: float
    hours_logged: Decimal
    project_resource_id: str | None
    response_status: str = "pending"
    can_manage: bool = False
    can_accept: bool = False
    can_decline: bool = False
    allocated_planned_hours: Decimal = Decimal(0)
    version: int = 1
    project_resource_version: int = 1
    capacity: TaskAssignmentCapacityFact | None = None

