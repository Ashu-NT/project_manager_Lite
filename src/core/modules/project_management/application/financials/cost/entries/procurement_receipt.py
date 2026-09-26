from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryRecorded,
)
from src.core.modules.project_management.contracts.financial_sources.procurement import (
    ProcurementReceiptAccrualFinancialSource,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
)
from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
        ProjectCostEntryService,
    )
    from src.core.modules.project_management.application.financials.procurement_consumer import (
        ProcurementExecutionContext,
    )


def apply_procurement_receipt_source(
    service: ProjectCostEntryService,
    source: ProcurementReceiptAccrualFinancialSource,
    *,
    execution: ProcurementExecutionContext,
) -> tuple[ProjectCostEntry, tuple[object, ...]]:
    """Post one trusted Procurement receipt fact without committing the inbox transaction.
    Returns the entry (its id is needed by the caller to match it to a Commitment line) and
    the real typed Cost Entry DomainEvent(s) produced -- a true replay returns an empty
    event tuple."""
    context = service._require_full_context("post Procurement receipt accrual")
    reference = source.reference
    if (
        reference.tenant_id != context.tenant_id
        or reference.organization_id != context.organization_id
    ):
        raise BusinessRuleError(
            "Procurement receipt source is outside the active scope.",
            code="PROCUREMENT_RECEIPT_SCOPE_MISMATCH",
        )
    service._require_project(reference.project_id)
    profile = service._require_active_profile(reference.project_id)
    if not profile.default_cost_code_id:
        raise BusinessRuleError(
            "Project requires a default cost code before receipt accruals can post.",
            code="PROCUREMENT_RECEIPT_DEFAULT_COST_CODE_REQUIRED",
        )
    posting_date = source.posted_at.date()
    service._require_dimensions(
        project_id=reference.project_id,
        cost_code_id=profile.default_cost_code_id,
        transaction_date=posting_date,
        task_id=source.task_id,
        resource_id=None,
        organization_id=context.organization_id,
    )
    quantity = source.accepted_quantity.to_domain()
    rate = source.unit_cost.to_domain()
    money = rate.apply(quantity).rounded()
    if money.currency.code != context.organization.base_currency:
        raise BusinessRuleError(
            "Cross-currency receipt accruals require an enterprise FX provider.",
            code="PROCUREMENT_RECEIPT_FX_PROVIDER_REQUIRED",
        )
    if money.amount <= 0:
        raise BusinessRuleError(
            "Procurement receipt accrual must be positive.",
            code="PROCUREMENT_RECEIPT_AMOUNT_INVALID",
        )
    existing = service._entry_repo.get_by_source_identity(reference, for_update=True)
    if existing is not None:
        if existing.idempotency_key == reference.idempotency_key:
            return service._resolve_replay(existing, reference), ()
        raise BusinessRuleError(
            "A changed receipt revision requires an explicit correction contract.",
            code="PROCUREMENT_RECEIPT_CORRECTION_CONTRACT_REQUIRED",
        )
    period = service._financial_period_service.require_open_period_for_integration(
        posting_date
    )
    actor_id = execution.service_principal.id
    now = service._clock.now()
    entry = ProjectCostEntry.create_draft(
        tenant_id=reference.tenant_id,
        organization_id=reference.organization_id,
        project_id=reference.project_id,
        description=f"Receipt accrual {source.receipt_number}",
        kind=ProjectCostEntryKind.ACTUAL,
        money=money,
        transaction_date=posting_date,
        cost_code_id=profile.default_cost_code_id,
        task_id=source.task_id,
        resource_id=None,
        source=reference,
        actor_id=actor_id,
        occurred_at=now,
    )
    entry.submit(actor_id=actor_id, occurred_at=now)
    entry.approve(actor_id=actor_id, occurred_at=now)
    entry.post(
        actor_id=actor_id,
        occurred_at=now,
        posting_date=posting_date,
        financial_period_id=period.id,
        base_money=money,
        exchange_rate=Decimal(1),
        exchange_rate_date=posting_date,
        exchange_rate_source="identity",
        exchange_rate_captured_at=now,
    )
    service._entry_repo.add(entry)
    service._entry_repo.flush()
    service._record_procurement_audit(
        "post_procurement_receipt",
        entry,
        execution=execution,
    )
    event = CostEntryRecorded(
        tenant_id=entry.tenant_id,
        organization_id=entry.organization_id,
        project_id=entry.project_id,
        cost_entry_id=entry.id,
        status=entry.status,
        occurred_at=now,
    )
    if service._record_event is not None:
        service._record_event(event)
    return entry, (event,)

