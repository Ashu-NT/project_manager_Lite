"""Map application facts to neutral responses."""

from __future__ import annotations

from src.core.modules.project_management.application.timesheets.dto.responses.workspace import (
    TimesheetResourcePageResponseDto,
    TimesheetResourceResponseDto,
    TimesheetWorkspaceAccessResponseDto,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetResourceFact,
    TimesheetResourceReadPage,
    TimesheetWorkspaceAccessFact,
)


def serialize_workspace_access(
    fact: TimesheetWorkspaceAccessFact,
) -> TimesheetWorkspaceAccessResponseDto:
    mine = fact.mine_resource
    return TimesheetWorkspaceAccessResponseDto(
        available_scopes=tuple(scope.value for scope in fact.available_scopes),
        default_scope=fact.default_scope.value,
        mine_resource_id=mine.resource_id if mine else "",
        mine_resource_name=mine.resource_name if mine else "",
    )


def serialize_timesheet_resource(
    fact: TimesheetResourceFact,
) -> TimesheetResourceResponseDto:
    return TimesheetResourceResponseDto(
        resource_id=fact.resource_id,
        resource_name=fact.resource_name,
        resource_code=fact.resource_code,
        kind=fact.kind,
        worker_type=fact.worker_type,
    )


def map_resource_page(page: TimesheetResourceReadPage) -> TimesheetResourcePageResponseDto:
    return TimesheetResourcePageResponseDto(
        items=tuple(serialize_timesheet_resource(item) for item in page.items),
        total=page.total, page=page.page, page_size=page.page_size,
    )
