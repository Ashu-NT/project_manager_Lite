from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .finance_budget_facts import FinancePageFacts


@dataclass(frozen=True, slots=True)
class FinanceSetupFacts:
    project_id: str
    currency_code: str
    status: str
    billing_method: str
    budget_control_mode: str
    cost_code_policy: str
    financial_start_date: date | None
    financial_end_date: date | None
    is_funded: bool
    is_billable: bool
    default_cost_code_id: str | None
    default_cost_code: str
    version: int


@dataclass(frozen=True, slots=True)
class FinanceSetupCostCodeQuery:
    page: int = 1
    page_size: int = 50
    search: str = ""
    status: str = ""
    assignment_state: str = ""
    sort_key: str = "code"
    sort_direction: str = "asc"

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))


@dataclass(frozen=True, slots=True)
class FinanceSetupRestrictionQuery:
    page: int = 1
    page_size: int = 50
    search: str = ""
    sort_key: str = "code"
    sort_direction: str = "asc"

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))


@dataclass(frozen=True, slots=True)
class FinanceSetupCostCodeFact:
    id: str
    code: str
    name: str
    description: str
    parent_id: str | None
    parent_code: str
    external_system: str | None
    external_reference: str | None
    effective_from: date | None
    effective_to: date | None
    is_active: bool
    is_assigned: bool
    is_default: bool
    version: int
    updated_at: datetime
    can_edit: bool = False
    can_change_status: bool = False
    can_add_restriction: bool = False
    can_remove_restriction: bool = False


@dataclass(frozen=True, slots=True)
class FinanceSetupRestrictionFact:
    id: str
    cost_code_id: str
    code: str
    name: str
    is_active: bool
    is_default: bool
    created_at: datetime
    can_remove: bool = False


@dataclass(frozen=True, slots=True)
class FinanceSetupWorkspaceFacts:
    profile: FinanceSetupFacts
    cost_codes: FinancePageFacts[FinanceSetupCostCodeFact]
    restrictions: FinancePageFacts[FinanceSetupRestrictionFact]
    can_edit_profile: bool = False
    can_transition_profile: bool = False
    can_create_cost_code: bool = False
    can_manage_restrictions: bool = False


__all__ = [
    "FinanceSetupCostCodeFact",
    "FinanceSetupCostCodeQuery",
    "FinanceSetupFacts",
    "FinanceSetupRestrictionFact",
    "FinanceSetupRestrictionQuery",
    "FinanceSetupWorkspaceFacts",
]
