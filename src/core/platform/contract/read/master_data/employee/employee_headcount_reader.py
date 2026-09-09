"""Employee headcount read contract.

Separate from ``EmployeeRepository`` (the write-side contract in ``contracts.py``): answers
"how many employees does this organization have, and how many are active" with one aggregate
query instead of fetching every ``Employee`` row and summing in Python.

``get_department_breakdown``/``get_site_breakdown`` return per-department/per-site aggregate
buckets (GROUP BY, one query each) for the cross-entity overview -- a different shape from
``EmployeeService.list_employees(department_id=...)``'s single-entity row-level fetch. Employees
with no department/site assigned are bucketed under a ``None`` id labeled "Unassigned".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmployeeHeadcountSummary:
    total: int
    active: int


@dataclass(frozen=True, slots=True)
class EmployeeDepartmentBreakdownRow:
    department_id: str | None
    department_name: str
    total: int
    active: int


@dataclass(frozen=True, slots=True)
class EmployeeSiteBreakdownRow:
    site_id: str | None
    site_name: str
    total: int
    active: int


class EmployeeHeadcountReader(Protocol):
    def get_summary(self, *, tenant_id: str, organization_id: str) -> EmployeeHeadcountSummary: ...

    def get_department_breakdown(
        self, *, tenant_id: str, organization_id: str
    ) -> tuple[EmployeeDepartmentBreakdownRow, ...]: ...

    def get_site_breakdown(
        self, *, tenant_id: str, organization_id: str
    ) -> tuple[EmployeeSiteBreakdownRow, ...]: ...


__all__ = [
    "EmployeeDepartmentBreakdownRow",
    "EmployeeHeadcountReader",
    "EmployeeHeadcountSummary",
    "EmployeeSiteBreakdownRow",
]
