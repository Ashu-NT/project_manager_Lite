from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class EmployeeCreated:
    tenant_id: str
    organization_id: str
    employee_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class EmployeeProfileUpdated:
    tenant_id: str
    organization_id: str
    employee_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class EmployeeActivated:
    tenant_id: str
    organization_id: str
    employee_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class EmployeeDeactivated:
    tenant_id: str
    organization_id: str
    employee_id: str
    occurred_at: datetime


__all__ = [
    "EmployeeActivated",
    "EmployeeCreated",
    "EmployeeDeactivated",
    "EmployeeProfileUpdated",
]
