from __future__ import annotations

from dataclasses import dataclass


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
    version: int


@dataclass(frozen=True)
class TaskTimeEntriesPageDesktopDto:
    items: tuple[TaskTimeEntryDesktopDto, ...]
    total: int
    page: int
    page_size: int


__all__ = [
    "TaskTimeEntriesPageDesktopDto",
    "TaskTimeEntryDesktopDto",
]
