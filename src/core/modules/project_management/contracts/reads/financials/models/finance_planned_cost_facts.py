from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .finance_budget_facts import FinancePageFacts


@dataclass(frozen=True, slots=True)
class PlannedCostVersionFact:
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
class PlannedCostLineFact:
    id: str
    version_id: str
    version_revision: int
    version_status: str
    task_name: str
    wbs_code: str
    resource_name: str
    resource_code: str
    cost_code: str
    cost_code_name: str
    planned_hours: Decimal
    rate_amount: Decimal
    amount: Decimal
    currency_code: str
    rate_card_id: str
    rate_card_version: int


@dataclass(frozen=True, slots=True)
class FinancePlannedCostWorkspaceFacts:
    selected_version_id: str
    versions: FinancePageFacts[PlannedCostVersionFact]
    lines: FinancePageFacts[PlannedCostLineFact]


__all__ = [
    "FinancePlannedCostWorkspaceFacts",
    "PlannedCostLineFact",
    "PlannedCostVersionFact",
]
