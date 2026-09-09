from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .finance_budget_facts import FinancePageFacts


_CHANGE_SORT_KEYS = {"title", "statusLabel", "subtitle", "supportingText", "metaText"}
_IMPACT_SORT_KEYS = {"title", "statusLabel", "subtitle", "supportingText", "metaText"}


@dataclass(frozen=True, slots=True)
class FinancialChangeRequestQuery:
    page: int = 1
    page_size: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "desc"
    search: str = ""
    status: str = ""
    approval_status: str = ""
    applied_state: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _CHANGE_SORT_KEYS else "metaText"


@dataclass(frozen=True, slots=True)
class FinancialChangeImpactQuery:
    page: int = 1
    page_size: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "asc"
    search: str = ""
    impact_type: str = ""
    applied_state: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _IMPACT_SORT_KEYS else "metaText"


@dataclass(frozen=True, slots=True)
class FinancialChangeSummaryFact:
    id: str
    title: str
    status: str
    revision: int
    row_version: int
    effective_date: date
    currency_code: str
    reason: str
    created_by: str
    base_budget_id: str | None
    base_budget_revision: int | None
    base_forecast_id: str | None
    base_forecast_revision: int | None
    approval_status: str
    impact_count: int
    created_at: datetime
    submitted_at: datetime | None
    applied_at: datetime | None


@dataclass(frozen=True, slots=True)
class FinancialChangeDetailFact:
    id: str
    title: str
    status: str
    revision: int
    row_version: int
    reason: str
    description: str
    effective_date: date
    currency_code: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    base_budget_id: str | None
    base_budget_revision: int | None
    current_budget_id: str | None
    current_budget_revision: int | None
    base_budget_is_current: bool | None
    base_forecast_id: str | None
    base_forecast_revision: int | None
    current_forecast_id: str | None
    current_forecast_revision: int | None
    base_forecast_is_current: bool | None
    approval_request_id: str | None
    approval_status: str
    approval_requested_by: str
    approval_requested_at: datetime | None
    approval_decided_by: str
    approval_decided_at: datetime | None
    approval_decision_note: str
    submitted_by: str | None
    submitted_at: datetime | None
    applied_by: str | None
    applied_at: datetime | None
    applied_budget_id: str | None
    applied_budget_revision: int | None
    applied_forecast_id: str | None
    applied_forecast_revision: int | None
    applied_schedule_count: int
    rejected_by: str | None
    rejected_at: datetime | None
    rejection_notes: str
    impact_count: int
    approval_requested_by_user_id: str | None = None
    can_edit: bool = False
    can_add_impact: bool = False
    can_submit: bool = False
    can_approve: bool = False
    can_reject: bool = False


@dataclass(frozen=True, slots=True)
class FinancialChangeImpactFact:
    id: str
    change_request_id: str
    impact_type: str
    description: str
    amount: Decimal
    currency_code: str | None
    cost_code_id: str | None
    cost_code: str
    cost_code_name: str
    task_id: str | None
    task_name: str
    wbs_code: str
    target_line_id: str | None
    target_task_version: int | None
    schedule_start: date | None
    schedule_finish: date | None
    applied_reference_type: str | None
    applied_reference_id: str | None
    row_version: int
    created_at: datetime
    updated_at: datetime
    can_edit: bool = False
    can_remove: bool = False


@dataclass(frozen=True, slots=True)
class FinanceChangeWorkspaceFacts:
    selected_change_id: str
    selected_change: FinancialChangeDetailFact | None
    changes: FinancePageFacts[FinancialChangeSummaryFact]
    impacts: FinancePageFacts[FinancialChangeImpactFact]
    can_create: bool = False


__all__ = [
    "FinanceChangeWorkspaceFacts",
    "FinancialChangeDetailFact",
    "FinancialChangeImpactFact",
    "FinancialChangeImpactQuery",
    "FinancialChangeRequestQuery",
    "FinancialChangeSummaryFact",
]
