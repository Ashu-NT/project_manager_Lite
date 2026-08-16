"""Employee headcount read contract
Separate from ``EmployeeRepository`` (the write-side contract in
``contracts.py``): a reader answers "how many employees does this
organization have, and how many are active" with one aggregate query,
instead of the admin overview's prior pattern of calling
``list_employees(active_only=None)`` -- the write repository's
``list_for_organization`` -- and summing over every fully-hydrated
``Employee`` row in Python just to produce two integers.

``get_department_breakdown``/``get_site_breakdown`` extend this with a
per-department/per-site GROUP BY aggregate (one query each), powering the
Platform Overview's "Employees by Department"/"Employees by Site" cards.
Unlike ``EmployeeService.list_employees(department_id=...)`` (a targeted
row-level fetch for one specific department/site, used by the department/
site detail pages), these return summary rows across ALL departments/sites
at once -- a different shape (aggregate buckets, not entity rows) for a
different consumer (the cross-entity overview, not a single-entity
drill-down). Employees with no department/site assigned are bucketed under
a ``None`` id labeled "Unassigned" rather than dropped.
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
