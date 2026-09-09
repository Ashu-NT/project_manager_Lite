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


@dataclass(frozen=True, slots=True, kw_only=True)
class FinancialChangeImpactCommand:
    change_id: str
    expected_change_version: int
    impact_type: str
    description: str
    amount: str = "0"
    currency_code: str = ""
    cost_code_id: str | None = None
    task_id: str | None = None
    target_line_id: str | None = None
    schedule_start: str = ""
    schedule_finish: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class FinancialUpdateChangeImpactCommand(FinancialChangeImpactCommand):
    impact_id: str
    expected_impact_version: int


@dataclass(frozen=True, slots=True)
class FinancialRemoveChangeImpactCommand:
    impact_id: str
    expected_impact_version: int
    expected_change_version: int


@dataclass(frozen=True, slots=True)
class FinancialSubmitChangeCommand:
    change_id: str
    expected_version: int


__all__ = [
    "FinancialChangeImpactCommand",
    "FinancialCreateChangeCommand",
    "FinancialRemoveChangeImpactCommand",
    "FinancialSubmitChangeCommand",
    "FinancialUpdateChangeCommand",
    "FinancialUpdateChangeImpactCommand",
]
