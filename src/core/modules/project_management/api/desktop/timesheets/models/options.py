from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimesheetOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TimesheetProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TimesheetAssignmentOptionDescriptor:
    value: str
    label: str
    project_id: str
    project_name: str
    task_id: str
    task_name: str
    resource_id: str
    resource_name: str


@dataclass(frozen=True)
class TimesheetPeriodOptionDescriptor:
    value: str
    label: str


__all__ = [
    "TimesheetAssignmentOptionDescriptor",
    "TimesheetOptionDescriptor",
    "TimesheetPeriodOptionDescriptor",
    "TimesheetProjectOptionDescriptor",
]
