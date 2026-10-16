from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourceProjectResponse:
    id: str
    resource_id: str
    project_id: str
    project_code: str
    project_name: str
    project_status: str
    planned_hours: str
    is_active: bool
    start_date: str
    end_date: str
    version: int
    can_open_project: bool



@dataclass(frozen=True, slots=True)
class ResourceProjectsPageResponse:
    items: tuple[ResourceProjectResponse, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "projectName"
    sort_direction: str = "asc"



@dataclass(frozen=True, slots=True)
class ResourceAssignmentResponse:
    id: str
    resource_id: str
    project_id: str
    project_code: str
    project_name: str
    task_id: str
    task_code: str
    task_name: str
    task_status: str
    scheduled_start: str
    scheduled_finish: str
    allocated_planned_hours: str
    allocation_percent: str
    actual_hours: str
    actual_hours_source: str
    response_status: str
    project_resource_id: str | None
    version: int
    can_open_project: bool
    can_open_task: bool



@dataclass(frozen=True, slots=True)
class ResourceAssignmentsPageResponse:
    items: tuple[ResourceAssignmentResponse, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "scheduledStart"
    sort_direction: str = "asc"




