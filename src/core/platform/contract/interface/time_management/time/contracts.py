from __future__ import annotations

from typing import Protocol


class WorkAllocationRecord(Protocol):
    id: str
    resource_id: str
    hours_logged: float


class WorkOwnerRecord(Protocol):
    id: str
    name: str


class WorkResourceRecord(Protocol):
    id: str
    name: str
    employee_id: str | None


WorkAssignmentRecord = WorkAllocationRecord
WorkTaskRecord = WorkOwnerRecord


__all__ = [
    "WorkAllocationRecord",
    "WorkAssignmentRecord",
    "WorkOwnerRecord",
    "WorkResourceRecord",
    "WorkTaskRecord",
]
