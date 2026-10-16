"""Map assignment aggregates once, retaining numeric and capacity facts."""

from decimal import Decimal

from src.core.modules.project_management.application.resources.capacity.task_assignment_capacity_service import (
    TaskAssignmentCapacityFact,
)
from src.core.modules.project_management.application.tasks.dto.responses.assignment import (
    TaskAssignmentResponseDto,
)
from src.core.modules.project_management.domain.tasks.task import TaskAssignment


def map_assignment(
    assignment: TaskAssignment,
    *,
    resource_name: str,
    project_resource_version: int = 1,
    can_manage: bool = False,
    can_accept: bool = False,
    can_decline: bool = False,
    capacity: TaskAssignmentCapacityFact | None = None,
) -> TaskAssignmentResponseDto:
    return TaskAssignmentResponseDto(
        id=assignment.id,
        task_id=assignment.task_id,
        resource_id=assignment.resource_id,
        resource_name=resource_name,
        allocation_percent=float(assignment.allocation_percent),
        hours_logged=Decimal(str(assignment.hours_logged)),
        allocated_planned_hours=Decimal(str(getattr(assignment, "allocated_planned_hours", 0))),
        project_resource_id=assignment.project_resource_id,
        response_status=getattr(assignment, "response_status", "pending") or "pending",
        version=int(getattr(assignment, "version", 1)),
        project_resource_version=project_resource_version,
        can_manage=can_manage,
        can_accept=can_accept,
        can_decline=can_decline,
        capacity=capacity,
    )
