"""Employee headcount read contract 
Separate from ``EmployeeRepository`` (the write-side contract in
``contracts.py``): a reader answers "how many employees does this
organization have, and how many are active" with one aggregate query,
instead of the admin overview's prior pattern of calling
``list_employees(active_only=None)`` -- the write repository's
``list_for_organization`` -- and summing over every fully-hydrated
``Employee`` row in Python just to produce two integers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmployeeHeadcountSummary:
    total: int
    active: int


class EmployeeHeadcountReader(Protocol):
    def get_summary(self, *, tenant_id: str, organization_id: str) -> EmployeeHeadcountSummary: ...


__all__ = ["EmployeeHeadcountReader", "EmployeeHeadcountSummary"]
