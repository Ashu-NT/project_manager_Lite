from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectResourceAssignCommand:
    project_id: str
    resource_id: str
    planned_hours: float = 0.0
    hourly_rate: float | None = None
    currency_code: str | None = None


@dataclass(frozen=True)
class ProjectResourceUpdateCommand:
    project_resource_id: str
    planned_hours: float = 0.0
    hourly_rate: float | None = None
    is_active: bool = True


__all__ = ["ProjectResourceAssignCommand", "ProjectResourceUpdateCommand"]
