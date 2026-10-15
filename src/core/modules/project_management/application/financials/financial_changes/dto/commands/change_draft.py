from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialCreateChangeCommand:
    project_id: str
    title: str
    reason: str
    effective_date: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class FinancialUpdateChangeCommand:
    change_id: str
    expected_version: int
    title: str
    reason: str
    effective_date: str
    description: str = ""


__all__ = ['FinancialCreateChangeCommand', 'FinancialUpdateChangeCommand']
