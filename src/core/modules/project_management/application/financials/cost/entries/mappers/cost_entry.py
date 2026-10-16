from __future__ import annotations

from src.core.modules.project_management.application.financials.cost.entries.capabilities import (
    CostEntryActionCapabilities,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.cost_entry import (
    CostEntryResponse,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
)


def map_cost_entry(
    entry: ProjectCostEntry, *, capabilities: CostEntryActionCapabilities
) -> CostEntryResponse:
    return CostEntryResponse(
        id=entry.id,
        tenant_id=entry.tenant_id,
        organization_id=entry.organization_id,
        project_id=entry.project_id,
        description=entry.description,
        entry_kind=entry.entry_kind,
        amount=entry.amount,
        currency_code=entry.currency_code,
        transaction_date=entry.transaction_date,
        cost_code_id=entry.cost_code_id,
        source_module=entry.source_module,
        source_type=entry.source_type,
        source_id=entry.source_id,
        source_revision=entry.source_revision,
        source_content_hash=entry.source_content_hash,
        posting_purpose=entry.posting_purpose,
        idempotency_key=entry.idempotency_key,
        source_line_id=entry.source_line_id,
        task_id=entry.task_id,
        resource_id=entry.resource_id,
        status=entry.status,
        base_amount=entry.base_amount,
        base_currency_code=entry.base_currency_code,
        exchange_rate=entry.exchange_rate,
        exchange_rate_date=entry.exchange_rate_date,
        exchange_rate_source=entry.exchange_rate_source,
        exchange_rate_captured_at=entry.exchange_rate_captured_at,
        posting_date=entry.posting_date,
        financial_period_id=entry.financial_period_id,
        reverses_entry_id=entry.reverses_entry_id,
        reversed_by_entry_id=entry.reversed_by_entry_id,
        row_version=entry.row_version,
        created_by=entry.created_by,
        created_at=entry.created_at,
        updated_by=entry.updated_by,
        updated_at=entry.updated_at,
        submitted_by=entry.submitted_by,
        submitted_at=entry.submitted_at,
        approved_by=entry.approved_by,
        approved_at=entry.approved_at,
        rejected_by=entry.rejected_by,
        rejected_at=entry.rejected_at,
        rejection_notes=entry.rejection_notes,
        posted_by=entry.posted_by,
        posted_at=entry.posted_at,
        reversed_by=entry.reversed_by,
        reversed_at=entry.reversed_at,
        is_manual_actual=entry.is_manual_actual,
        capabilities=capabilities,
    )
