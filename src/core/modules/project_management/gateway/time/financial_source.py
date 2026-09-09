"""PM-owned port for pulling Approved Time financial-source facts from
Platform Time.

Mirrors `gateway.task.reservation.TaskReservationGateway`, but currently has zero
implementations: Platform Time delivers Approved Time facts exclusively through the
push-based outbox/inbox event path (see `ApprovedTimeLaborCostConsumer`), not through
this pull contract. Retained as a declared, forward-looking alternative -- not wired
into any runtime composition today.
"""

from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.financial_sources.approved_time import (
    ApprovedTimeFinancialSource,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialSourcePage,
)


class ApprovedTimeFinancialSourceProvider(Protocol):
    def list_approved_time_sources(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> FinancialSourcePage[ApprovedTimeFinancialSource]: ...


__all__ = ["ApprovedTimeFinancialSourceProvider"]
