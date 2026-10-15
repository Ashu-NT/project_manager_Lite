"""Unwired, future-facing Procurement financial-source query boundary.

PM currently consumes neutral Procurement facts through its durable event/inbox
path, not this pull contract. Procurement operations will belong to a future
Procurement module. This declaration is not a second production truth path.
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
