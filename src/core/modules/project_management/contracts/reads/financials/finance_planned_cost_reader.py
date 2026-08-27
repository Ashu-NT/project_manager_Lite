from __future__ import annotations

from typing import Protocol

from .models.finance_budget_facts import FinancePageFacts, FinancePageRequest
from .models.finance_planned_cost_facts import (
    PlannedCostLineFact,
    PlannedCostVersionFact,
)


class FinancePlannedCostReader(Protocol):
    def list_versions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinancePageRequest,
    ) -> FinancePageFacts[PlannedCostVersionFact]: ...

    def list_lines(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        version_id: str,
        request: FinancePageRequest,
    ) -> FinancePageFacts[PlannedCostLineFact]: ...


__all__ = ["FinancePlannedCostReader"]
