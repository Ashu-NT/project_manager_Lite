from __future__ import annotations

from src.core.modules.project_management.application.resources.dto.responses.context import (
    ResourceAssignmentResponse,
    ResourceAssignmentsPageResponse,
    ResourceProjectResponse,
    ResourceProjectsPageResponse,
)
from src.core.modules.project_management.contracts.reads.resources.models import (
    ResourceAssignmentFact,
    ResourceAssignmentReadPage,
    ResourceProjectFact,
    ResourceProjectReadPage,
)


def map_resource_project_fact(value: ResourceProjectFact) -> ResourceProjectResponse:
    return ResourceProjectResponse(
        id=value.project_resource_id,
        resource_id=value.resource_id,
        project_id=value.project_id,
        project_code=value.project_code,
        project_name=value.project_name,
        project_status=value.project_status,
        planned_hours=str(value.planned_hours),
        is_active=value.is_active,
        start_date=value.start_date.isoformat() if value.start_date else "",
        end_date=value.end_date.isoformat() if value.end_date else "",
        version=value.version,
        can_open_project=value.can_open_project,
    )


def map_resource_project_read_page(value: ResourceProjectReadPage) -> ResourceProjectsPageResponse:
    return ResourceProjectsPageResponse(
        items=tuple(map_resource_project_fact(item) for item in value.items),
        filtered_total=value.filtered_total,
        page=value.page,
        page_size=value.page_size,
        sort_key=value.sort.key,
        sort_direction=value.sort.direction.value,
    )


def map_resource_assignment_fact(
    value: ResourceAssignmentFact,
) -> ResourceAssignmentResponse:
    return ResourceAssignmentResponse(
        id=value.assignment_id,
        resource_id=value.resource_id,
        project_id=value.project_id,
        project_code=value.project_code,
        project_name=value.project_name,
        task_id=value.task_id,
        task_code=value.task_code,
        task_name=value.task_name,
        task_status=value.task_status,
        scheduled_start=value.scheduled_start.isoformat() if value.scheduled_start else "",
        scheduled_finish=value.scheduled_finish.isoformat() if value.scheduled_finish else "",
        allocated_planned_hours=str(value.allocated_planned_hours),
        allocation_percent=str(value.allocation_percent),
        actual_hours=str(value.actual_hours),
        actual_hours_source=value.actual_hours_source,
        response_status=value.response_status,
        project_resource_id=value.project_resource_id,
        version=value.assignment_version,
        can_open_project=value.can_open_project,
        can_open_task=value.can_open_task,
    )


def map_resource_assignment_read_page(value: ResourceAssignmentReadPage) -> ResourceAssignmentsPageResponse:
    return ResourceAssignmentsPageResponse(
        items=tuple(map_resource_assignment_fact(item) for item in value.items),
        filtered_total=value.filtered_total,
        page=value.page,
        page_size=value.page_size,
        sort_key=value.sort.key,
        sort_direction=value.sort.direction.value,
    )




