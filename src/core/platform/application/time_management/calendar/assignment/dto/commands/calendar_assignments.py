"""Calendar calendar assignments inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SiteCalendarAssignCommand:
    site_id: str
    calendar_id: str
    effective_from: date | str | None = None
    effective_to: date | str | None = None
    is_default: bool = True
    priority: int = 0


@dataclass(frozen=True)
class DeptCalendarAssignCommand:
    department_id: str
    calendar_id: str
    effective_from: date | str | None = None
    effective_to: date | str | None = None
    is_default: bool = True
    priority: int = 0


@dataclass(frozen=True)
class EmpCalendarAssignCommand:
    employee_id: str
    calendar_id: str
    effective_from: date | str | None = None
    effective_to: date | str | None = None
    is_default: bool = True
    priority: int = 0


@dataclass(frozen=True)
class ProjectCalendarAssignCommand:
    project_id: str
    calendar_id: str
    effective_from: date | str | None = None
    effective_to: date | str | None = None
    is_default: bool = True
    priority: int = 0


@dataclass(frozen=True)
class ResourceCalendarAssignCommand:
    resource_id: str
    calendar_id: str
    effective_from: date | str | None = None
    effective_to: date | str | None = None
    is_default: bool = True
    priority: int = 0
