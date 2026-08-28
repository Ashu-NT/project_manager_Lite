from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class DepartmentCreated:
    tenant_id: str
    organization_id: str
    department_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class DepartmentProfileUpdated:
    tenant_id: str
    organization_id: str
    department_id: str
    occurred_at: datetime


__all__ = ["DepartmentCreated", "DepartmentProfileUpdated"]
