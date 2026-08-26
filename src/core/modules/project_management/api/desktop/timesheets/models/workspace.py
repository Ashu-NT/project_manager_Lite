from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TimesheetWorkspaceAccessDesktopDto:
    available_scopes: tuple[str, ...]
    default_scope: str
    mine_resource_id: str = ""
    mine_resource_name: str = ""


@dataclass(frozen=True, slots=True)
class TimesheetResourceDesktopDto:
    resource_id: str
    resource_name: str
    resource_code: str
    kind: str
    worker_type: str


@dataclass(frozen=True, slots=True)
class TimesheetResourcePageDesktopDto:
    items: tuple[TimesheetResourceDesktopDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True, slots=True)
class ResourceTimesheetPeriodDesktopDto:
    period_id: str
    resource_id: str
    resource_name: str
    resource_code: str
    resource_kind: str
    worker_type: str
    period_start: date
    period_end: date
    period_label: str
    status: str
    status_label: str
    version: int
    total_hours: float
    total_hours_label: str
    entry_count: int
    project_count: int
    task_count: int
    submitted_at_label: str
    decided_at_label: str
    return_reason: str
    can_add_entry: bool
    can_edit_entry: bool
    can_delete_entry: bool
    can_submit: bool
    can_resubmit: bool
    can_view_return_reason: bool
    can_view_history: bool


@dataclass(frozen=True, slots=True)
class ResourceTimesheetEntryDesktopDto:
    entry_id: str
    assignment_id: str
    work_date: date
    work_date_label: str
    hours: float
    hours_label: str
    description: str
    project_id: str
    project_code: str
    project_name: str
    task_id: str
    task_code: str
    task_name: str
    activity_type: str
    version: int
    can_edit: bool
    can_delete: bool


@dataclass(frozen=True, slots=True)
class ResourceTimesheetEntryPageDesktopDto:
    items: tuple[ResourceTimesheetEntryDesktopDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "date"
    sort_direction: str = "desc"


@dataclass(frozen=True, slots=True)
class ResourceTimesheetHistoryPageDesktopDto:
    items: tuple[ResourceTimesheetPeriodDesktopDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 12


__all__ = [
    "ResourceTimesheetEntryDesktopDto",
    "ResourceTimesheetEntryPageDesktopDto",
    "ResourceTimesheetHistoryPageDesktopDto",
    "ResourceTimesheetPeriodDesktopDto",
    "TimesheetResourceDesktopDto",
    "TimesheetResourcePageDesktopDto",
    "TimesheetWorkspaceAccessDesktopDto",
]
