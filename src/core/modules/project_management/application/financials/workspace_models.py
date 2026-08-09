from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.core.modules.project_management.domain.financials.configuration import (
    ProjectFinancialProfile,
)


@dataclass(frozen=True, slots=True)
class FinanceBudgetVersionRead:
    id: str
    name: str
    status: str
    revision: int
    row_version: int
    currency_code: str
    line_count: int
    total_amount: Decimal
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    notes: str


@dataclass(frozen=True, slots=True)
class FinanceBudgetLineRead:
    id: str
    budget_id: str
    budget_name: str
    budget_revision: int
    budget_status: str
    description: str
    cost_code: str
    cost_code_name: str
    task_name: str
    wbs_code: str
    amount: Decimal
    currency_code: str


@dataclass(frozen=True, slots=True)
class FinanceRateCardRead:
    id: str
    name: str
    scope: str
    is_active: bool
    is_legacy: bool
    version: int
    line_count: int


@dataclass(frozen=True, slots=True)
class FinanceRateLineRead:
    id: str
    rate_card_id: str
    rate_card_name: str
    card_scope: str
    rate_type: str
    origin: str
    rate_amount: Decimal
    rate_currency: str
    unit: str
    resource_name: str
    role: str
    skill_code: str
    department_id: str
    effective_from: date | None
    effective_to: date | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class FinancePlannedCostVersionRead:
    id: str
    revision: int
    status: str
    currency_code: str
    as_of: date
    calculated_by: str
    calculated_at: datetime
    line_count: int
    total_hours: Decimal
    total_amount: Decimal
    rates_complete: bool
    allocations_complete: bool
    cost_codes_complete: bool
    unresolved_rate_count: int
    partially_allocated_resource_count: int
    unclassified_line_count: int


@dataclass(frozen=True, slots=True)
class FinancePlannedCostLineRead:
    id: str
    version_id: str
    version_revision: int
    version_status: str
    task_name: str
    wbs_code: str
    resource_name: str
    cost_code: str
    cost_code_name: str
    planned_hours: Decimal
    rate_amount: Decimal
    amount: Decimal
    currency_code: str
    rate_card_id: str
    rate_card_version: int


@dataclass(frozen=True, slots=True)
class ProjectFinanceWorkspaceRead:
    project_id: str
    profile: ProjectFinancialProfile
    default_cost_code: str
    budget_versions: tuple[FinanceBudgetVersionRead, ...]
    budget_lines: tuple[FinanceBudgetLineRead, ...]
    budget_line_page: int
    budget_line_page_size: int
    budget_line_total: int
    rate_cards: tuple[FinanceRateCardRead, ...]
    rate_lines: tuple[FinanceRateLineRead, ...]
    rate_line_page: int
    rate_line_page_size: int
    rate_line_total: int
    planned_cost_versions: tuple[FinancePlannedCostVersionRead, ...]
    planned_cost_lines: tuple[FinancePlannedCostLineRead, ...]
    planned_cost_line_page: int
    planned_cost_line_page_size: int
    planned_cost_line_total: int


__all__ = [
    "FinanceBudgetLineRead",
    "FinanceBudgetVersionRead",
    "FinancePlannedCostLineRead",
    "FinancePlannedCostVersionRead",
    "FinanceRateCardRead",
    "FinanceRateLineRead",
    "ProjectFinanceWorkspaceRead",
]
