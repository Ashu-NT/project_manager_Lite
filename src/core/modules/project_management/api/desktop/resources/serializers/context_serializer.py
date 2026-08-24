from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.models.context import (
    ResourceActivityDesktopDto,
    ResourceAssignmentDesktopDto,
    ResourceProjectDesktopDto,
)
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceActivityFact,
    ResourceAssignmentFact,
    ResourceProjectFact,
)


def serialize_resource_project(fact: ResourceProjectFact) -> ResourceProjectDesktopDto:
    return ResourceProjectDesktopDto(
        id=fact.project_resource_id,
        resource_id=fact.resource_id,
        project_id=fact.project_id,
        project_code=fact.project_code,
        project_name=fact.project_name,
        project_status=fact.project_status,
        planned_hours=str(fact.planned_hours),
        is_active=fact.is_active,
        start_date=fact.start_date.isoformat() if fact.start_date else "",
        end_date=fact.end_date.isoformat() if fact.end_date else "",
        version=fact.version,
        can_open_project=fact.can_open_project,
    )


def serialize_resource_assignment(
    fact: ResourceAssignmentFact,
) -> ResourceAssignmentDesktopDto:
    return ResourceAssignmentDesktopDto(
        id=fact.assignment_id,
        resource_id=fact.resource_id,
        project_id=fact.project_id,
        project_code=fact.project_code,
        project_name=fact.project_name,
        task_id=fact.task_id,
        task_code=fact.task_code,
        task_name=fact.task_name,
        task_status=fact.task_status,
        scheduled_start=fact.scheduled_start.isoformat() if fact.scheduled_start else "",
        scheduled_finish=fact.scheduled_finish.isoformat() if fact.scheduled_finish else "",
        allocated_planned_hours=str(fact.allocated_planned_hours),
        allocation_percent=str(fact.allocation_percent),
        actual_hours=str(fact.actual_hours),
        actual_hours_source=fact.actual_hours_source,
        response_status=fact.response_status,
        project_resource_id=fact.project_resource_id,
        version=fact.assignment_version,
        can_open_project=fact.can_open_project,
        can_open_task=fact.can_open_task,
    )


def serialize_resource_activity(fact: ResourceActivityFact) -> ResourceActivityDesktopDto:
    return ResourceActivityDesktopDto(
        id=fact.activity_id,
        resource_id=fact.resource_id,
        occurred_at=fact.occurred_at.isoformat(),
        event_type=fact.event_type,
        category=fact.category,
        actor_label=fact.actor_label,
        summary=fact.summary,
        source_type=fact.source_type,
        source_id=fact.source_id,
        project_id=fact.project_id,
        task_id=fact.task_id,
        can_open_source=fact.can_open_source,
    )


__all__ = [
    "serialize_resource_activity",
    "serialize_resource_assignment",
    "serialize_resource_project",
]
