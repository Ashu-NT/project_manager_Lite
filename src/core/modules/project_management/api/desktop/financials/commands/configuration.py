from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FinancialCreateCostCodeCommand:
    project_id: str
    code: str
    name: str
    description: str = ""
    parent_id: str | None = None
    external_system: str | None = None
    external_reference: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class FinancialUpdateProfileCommand:
    project_id: str
    expected_version: int
    currency_code: str
    billing_method: str
    budget_control_mode: str
    cost_code_policy: str
    financial_start_date: date | None
    financial_end_date: date | None
    is_funded: bool
    is_billable: bool
    default_cost_code_id: str | None


@dataclass(frozen=True, slots=True)
class FinancialTransitionProfileCommand:
    project_id: str
    expected_version: int
    target_status: str


@dataclass(frozen=True, slots=True)
class FinancialUpdateCostCodeCommand:
    cost_code_id: str
    expected_version: int
    code: str
    name: str
    description: str
    parent_id: str | None
    external_system: str | None
    external_reference: str | None
    effective_from: date | None
    effective_to: date | None


@dataclass(frozen=True, slots=True)
class FinancialChangeCostCodeStatusCommand:
    cost_code_id: str
    expected_version: int
    activate: bool


@dataclass(frozen=True, slots=True)
class FinancialCostCodeRestrictionCommand:
    project_id: str
    cost_code_id: str


__all__ = [
    "FinancialChangeCostCodeStatusCommand",
    "FinancialCostCodeRestrictionCommand",
    "FinancialCreateCostCodeCommand",
    "FinancialTransitionProfileCommand",
    "FinancialUpdateCostCodeCommand",
    "FinancialUpdateProfileCommand",
]
