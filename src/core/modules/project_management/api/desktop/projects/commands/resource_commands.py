from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProjectResourceAssignCommand:
    project_id: str
    resource_id: str
    planned_hours: Decimal = Decimal("0")
    hourly_rate: Decimal | None = None
    currency_code: str | None = None


@dataclass(frozen=True)
class ProjectResourceUpdateCommand:
    project_resource_id: str
    planned_hours: Decimal = Decimal("0")
    hourly_rate: Decimal | None = None
    is_active: bool = True
    expected_version: int | None = None


__all__ = ["ProjectResourceAssignCommand", "ProjectResourceUpdateCommand"]
