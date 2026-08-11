from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialCommitmentSummaryDto:
    project_id: str
    approved_budget: float
    approved_budget_label: str
    posted_actual: float
    posted_actual_label: str
    open_commitment: float
    open_commitment_label: str
    available_after_commitment: float | None
    available_after_commitment_label: str
    commitment_rate_pct: float


@dataclass(frozen=True)
class FinancialCommitmentLineDto:
    id: str
    purchase_order_line_id: str
    state: str
    amount_label: str
    matched_amount_label: str
    remaining_amount_label: str
    task_id: str
    quantity_label: str
    order_date: str
    expected_delivery_date: str
    source_revision: int


@dataclass(frozen=True)
class FinancialCommitmentLinePageDto:
    items: tuple[FinancialCommitmentLineDto, ...] = ()
    total: int = 0
    offset: int = 0
    limit: int = 50


__all__ = [
    "FinancialCommitmentLineDto",
    "FinancialCommitmentLinePageDto",
    "FinancialCommitmentSummaryDto",
]
