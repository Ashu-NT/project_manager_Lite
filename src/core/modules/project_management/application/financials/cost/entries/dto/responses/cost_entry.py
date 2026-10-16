from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.core.modules.project_management.application.financials.cost.entries.capabilities import (
    CostEntryActionCapabilities,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceType,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)


@dataclass(frozen=True, slots=True)
class CostEntryResponse:
    """Detached cost evidence and server-authored actions; no lifecycle methods."""

    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    description: str
    entry_kind: ProjectCostEntryKind
    amount: Decimal
    currency_code: str
    transaction_date: date
    cost_code_id: str
    source_module: FinancialSourceModule
    source_type: FinancialSourceType
    source_id: str
    source_revision: str
    source_content_hash: str
    posting_purpose: FinancialPostingPurpose
    idempotency_key: str
    source_line_id: str | None
    task_id: str | None
    resource_id: str | None
    status: ProjectCostEntryStatus
    base_amount: Decimal | None
    base_currency_code: str | None
    exchange_rate: Decimal | None
    exchange_rate_date: date | None
    exchange_rate_source: str | None
    exchange_rate_captured_at: datetime | None
    posting_date: date | None
    financial_period_id: str | None
    reverses_entry_id: str | None
    reversed_by_entry_id: str | None
    row_version: int
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    rejected_by: str | None
    rejected_at: datetime | None
    rejection_notes: str
    posted_by: str | None
    posted_at: datetime | None
    reversed_by: str | None
    reversed_at: datetime | None
    is_manual_actual: bool
    capabilities: CostEntryActionCapabilities
