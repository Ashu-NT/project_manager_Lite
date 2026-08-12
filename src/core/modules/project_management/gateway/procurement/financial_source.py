"""PM-owned port for pulling Procurement commitment and receipt-accrual
financial-source facts from Inventory/Procurement.

Mirrors `gateway.task.reservation.TaskReservationGateway`: PM defines the
shape it would need; unlike that gateway, this one currently has zero
implementations anywhere in the codebase (Inventory/Procurement delivers
these facts exclusively through the push-based outbox/inbox event path --
see `ProcurementFinancialDispatcher` and `application.financials.
procurement_consumer` -- not through this pull contract). It is retained
as a declared, forward-looking pull alternative and is not wired into any
runtime composition today.
"""

from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.financial_sources.procurement import (
    ProcurementCommitmentFinancialSource,
    ProcurementReceiptAccrualFinancialSource,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialSourcePage,
)


class ProcurementFinancialSourceProvider(Protocol):
    def list_commitment_sources(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> FinancialSourcePage[ProcurementCommitmentFinancialSource]: ...

    def list_receipt_accrual_sources(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> FinancialSourcePage[ProcurementReceiptAccrualFinancialSource]: ...


__all__ = ["ProcurementFinancialSourceProvider"]
