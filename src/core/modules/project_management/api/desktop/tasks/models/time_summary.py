from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskResourceTimeBreakdownDesktopDto:
    assignment_id: str
    resource_id: str
    resource_name: str
    planned_hours_label: str
    actual_hours_label: str
    remaining_hours_label: str
    overrun_hours_label: str
    has_overrun: bool
    burn_status: str
    burn_status_label: str


@dataclass(frozen=True)
class TaskTimeSummaryDesktopDto:
    task_id: str
    planned_hours_label: str
    actual_hours_label: str
    remaining_hours_label: str
    overrun_hours_label: str
    has_overrun: bool
    burn_status: str
    burn_status_label: str
    assignment_count: int
    resource_breakdown: tuple[TaskResourceTimeBreakdownDesktopDto, ...] = ()


@dataclass(frozen=True)
class TaskTimeEntryDesktopDto:
    entry_id: str
    assignment_id: str
    resource_id: str
    resource_name: str
    entry_date_label: str
    hours: float
    hours_label: str
    note: str
    author_username: str


@dataclass(frozen=True)
class TaskTimeEntriesPageDesktopDto:
    items: tuple[TaskTimeEntryDesktopDto, ...]
    total: int
    page: int
    page_size: int


__all__ = [
    "TaskResourceTimeBreakdownDesktopDto",
    "TaskTimeEntriesPageDesktopDto",
    "TaskTimeEntryDesktopDto",
    "TaskTimeSummaryDesktopDto",
]
