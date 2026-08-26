from __future__ import annotations

from src.core.modules.project_management.api.desktop.timesheets.formatters.datetime_formatter import format_datetime
from src.core.modules.project_management.api.desktop.timesheets.formatters.time_formatter import format_hours
from src.core.modules.project_management.api.desktop.timesheets.models.workspace import (
    ResourceTimesheetEntryDesktopDto,
    ResourceTimesheetPeriodDesktopDto,
    TimesheetResourceDesktopDto,
    TimesheetWorkspaceAccessDesktopDto,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetEntryFact,
    TimesheetPeriodFact,
    TimesheetResourceFact,
    TimesheetWorkspaceAccessFact,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


_STATUS_LABELS = {
    TimesheetPeriodStatus.OPEN: "Open",
    TimesheetPeriodStatus.SUBMITTED: "Awaiting Review",
    TimesheetPeriodStatus.APPROVED: "Approved",
    TimesheetPeriodStatus.REJECTED: "Returned",
    TimesheetPeriodStatus.LOCKED: "Locked",
}


def serialize_workspace_access(fact: TimesheetWorkspaceAccessFact) -> TimesheetWorkspaceAccessDesktopDto:
    mine = fact.mine_resource
    return TimesheetWorkspaceAccessDesktopDto(
        available_scopes=tuple(scope.value for scope in fact.available_scopes),
        default_scope=fact.default_scope.value,
        mine_resource_id=mine.resource_id if mine else "",
        mine_resource_name=mine.resource_name if mine else "",
    )


def serialize_timesheet_resource(fact: TimesheetResourceFact) -> TimesheetResourceDesktopDto:
    return TimesheetResourceDesktopDto(
        resource_id=fact.resource_id,
        resource_name=fact.resource_name,
        resource_code=fact.resource_code,
        kind=fact.kind,
        worker_type=fact.worker_type,
    )


def serialize_resource_period(fact: TimesheetPeriodFact) -> ResourceTimesheetPeriodDesktopDto:
    return ResourceTimesheetPeriodDesktopDto(
        period_id=fact.period_id,
        resource_id=fact.resource_id,
        resource_name=fact.resource_name,
        resource_code=fact.resource_code,
        resource_kind=fact.resource_kind,
        worker_type=fact.worker_type,
        period_start=fact.period_start,
        period_end=fact.period_end,
        period_label=f"{fact.period_start:%d %b %Y} - {fact.period_end:%d %b %Y}",
        status=fact.status.value,
        status_label=_STATUS_LABELS[fact.status],
        version=fact.version,
        total_hours=float(fact.total_hours),
        total_hours_label=format_hours(fact.total_hours),
        entry_count=fact.entry_count,
        project_count=fact.project_count,
        task_count=fact.task_count,
        submitted_at_label=format_datetime(fact.submitted_at),
        decided_at_label=format_datetime(fact.decided_at),
        return_reason=fact.decision_note if fact.can_view_return_reason else "",
        can_add_entry=fact.can_add_entry,
        can_edit_entry=fact.can_edit_entry,
        can_delete_entry=fact.can_delete_entry,
        can_submit=fact.can_submit,
        can_resubmit=fact.can_resubmit,
        can_view_return_reason=fact.can_view_return_reason,
        can_view_history=fact.can_view_history,
    )


def serialize_resource_entry(fact: TimesheetEntryFact) -> ResourceTimesheetEntryDesktopDto:
    return ResourceTimesheetEntryDesktopDto(
        entry_id=fact.entry_id,
        assignment_id=fact.assignment_id,
        work_date=fact.work_date,
        work_date_label=fact.work_date.strftime("%d %b %Y"),
        hours=float(fact.hours),
        hours_label=format_hours(fact.hours),
        description=fact.description,
        project_id=fact.project_id or "",
        project_code=fact.project_code,
        project_name=fact.project_name,
        task_id=fact.task_id or "",
        task_code=fact.task_code,
        task_name=fact.task_name,
        activity_type=fact.activity_type,
        version=fact.version,
        can_edit=fact.can_edit,
        can_delete=fact.can_delete,
    )


__all__ = [
    "serialize_resource_entry",
    "serialize_resource_period",
    "serialize_timesheet_resource",
    "serialize_workspace_access",
]
