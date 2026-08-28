from __future__ import annotations

from typing import Protocol

from .models.finance_budget_facts import FinancePageFacts
from .models.finance_change_facts import (
    FinancialChangeDetailFact,
    FinancialChangeImpactFact,
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
    FinancialChangeSummaryFact,
)


class FinanceChangeReader(Protocol):
    def list_changes(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinancialChangeRequestQuery,
    ) -> FinancePageFacts[FinancialChangeSummaryFact]: ...

    def get_change(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        change_id: str,
    ) -> FinancialChangeDetailFact | None: ...

    def list_impacts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        change_id: str,
        request: FinancialChangeImpactQuery,
    ) -> FinancePageFacts[FinancialChangeImpactFact]: ...


__all__ = ["FinanceChangeReader"]
