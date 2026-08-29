from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .finance_budget_facts import FinancePageFacts


_SCHEDULE_SORT_KEYS = {"title", "statusLabel", "subtitle", "supportingText", "metaText"}
_PREPARATION_SORT_KEYS = {"title", "statusLabel", "subtitle", "supportingText", "metaText"}
_LINE_SORT_KEYS = {"title", "statusLabel", "subtitle", "supportingText", "metaText"}
_ACCOUNTING_SORT_KEYS = {"title", "statusLabel", "metaText"}


@dataclass(frozen=True, slots=True)
class AccountingStatusQuery:
    page: int = 1
    page_size: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "desc"
    search: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _ACCOUNTING_SORT_KEYS else "metaText"


@dataclass(frozen=True, slots=True)
class BillingScheduleQuery:
    page: int = 1
    page_size: int = 50
    sort_key: str = "supportingText"
    sort_direction: str = "asc"
    search: str = ""
    status: str = ""
    source_state: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _SCHEDULE_SORT_KEYS else "supportingText"


@dataclass(frozen=True, slots=True)
class BillingPreparationQuery:
    page: int = 1
    page_size: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "desc"
    search: str = ""
    status: str = ""
    billing_method: str = ""
    approval_status: str = ""
    delivery_state: str = ""
    correction_state: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _PREPARATION_SORT_KEYS else "metaText"


@dataclass(frozen=True, slots=True)
class BillingPreparationLineQuery:
    page: int = 1
    page_size: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "asc"
    search: str = ""
    source_type: str = ""
    source_state: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _LINE_SORT_KEYS else "metaText"


@dataclass(frozen=True, slots=True)
class BillingProfileFact:
    id: str
    status: str
    currency_code: str
    contract_reference: str
    contract_value: Decimal
    customer_party_id: str | None
    external_customer_reference: str | None
    purchase_order_reference: str | None
    cost_plus_markup_percent: Decimal
    payment_terms_days: int
    retention_years: int
    legal_hold: bool
    row_version: int


@dataclass(frozen=True, slots=True)
class BillingScheduleFact:
    id: str
    name: str
    status: str
    amount: Decimal
    currency_code: str
    due_date: date
    task_id: str | None
    task_name: str
    task_wbs_code: str
    acceptance_reference: str | None
    source_state: str
    row_version: int


@dataclass(frozen=True, slots=True)
class BillingPreparationSummaryFact:
    id: str
    preparation_number: str
    billing_method: str
    period_start: date
    period_end: date
    status: str
    approval_status: str
    currency_code: str
    line_count: int
    total_amount: Decimal
    correction_of_preparation_id: str | None
    correction_of_preparation_number: str
    delivery_requested_at: datetime | None
    latest_external_event_type: str
    latest_external_status: str
    latest_external_system: str
    latest_external_occurred_at: datetime | None
    created_at: datetime
    submitted_at: datetime | None
    approved_at: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class BillingPreparationDetailFact:
    id: str
    preparation_number: str
    billing_method: str
    period_start: date
    period_end: date
    status: str
    currency_code: str
    line_count: int
    total_amount: Decimal
    correction_of_preparation_id: str | None
    correction_of_preparation_number: str
    approval_request_id: str | None
    approval_status: str
    approval_requested_by: str
    approval_requested_at: datetime | None
    approval_decided_by: str
    approval_decided_at: datetime | None
    approval_decision_note: str
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    rejected_by: str | None
    rejected_at: datetime | None
    rejection_notes: str
    delivery_requested_at: datetime | None
    delivered_at: datetime | None
    acknowledged_at: datetime | None
    reconciled_at: datetime | None
    lock_count: int
    reserved_lock_count: int
    finalized_lock_count: int
    released_lock_count: int
    latest_external_event_type: str
    latest_external_system: str
    latest_external_status: str
    latest_external_invoice_reference: str
    latest_reconciliation_reference: str
    latest_external_message: str
    latest_external_occurred_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    row_version: int


@dataclass(frozen=True, slots=True)
class BillingPreparationLineFact:
    id: str
    preparation_id: str
    source_type: str
    source_id: str
    source_revision: str
    description: str
    source_date: date
    quantity: Decimal
    unit: str
    unit_rate: Decimal
    net_amount: Decimal
    currency_code: str
    task_id: str | None
    resource_id: str | None
    source_amount: Decimal | None
    markup_percent: Decimal | None
    rate_card_id: str | None
    rate_line_id: str | None
    rate_card_version: int | None
    source_state: str


@dataclass(frozen=True, slots=True)
class AccountingStatusFact:
    id: str
    preparation_number: str
    preparation_status: str
    correction_of_preparation_id: str | None
    correction_of_preparation_number: str
    delivery_requested_at: datetime | None
    latest_external_event_type: str
    latest_external_system: str
    latest_external_status: str
    latest_external_invoice_reference: str
    latest_reconciliation_reference: str
    latest_external_message: str
    latest_external_occurred_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FinanceBillingWorkspaceFacts:
    profile: BillingProfileFact | None
    selected_preparation_id: str
    selected_preparation: BillingPreparationDetailFact | None
    schedule: FinancePageFacts[BillingScheduleFact]
    preparations: FinancePageFacts[BillingPreparationSummaryFact]
    lines: FinancePageFacts[BillingPreparationLineFact]


__all__ = [
    "AccountingStatusFact",
    "AccountingStatusQuery",
    "BillingPreparationDetailFact",
    "BillingPreparationLineFact",
    "BillingPreparationLineQuery",
    "BillingPreparationQuery",
    "BillingPreparationSummaryFact",
    "BillingProfileFact",
    "BillingScheduleFact",
    "BillingScheduleQuery",
    "FinanceBillingWorkspaceFacts",
]
