from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectResourceDesktopDto:
    id: str
    project_id: str
    resource_id: str
    resource_name: str
    role: str
    worker_type_label: str
    hourly_rate: str | None
    hourly_rate_label: str
    currency_code: str | None
    planned_hours: str
    planned_hours_label: str
    is_active: bool
    status_label: str


@dataclass(frozen=True)
class ProjectAssignableResourceOptionDescriptor:
    value: str
    label: str


__all__ = ["ProjectAssignableResourceOptionDescriptor", "ProjectResourceDesktopDto"]
