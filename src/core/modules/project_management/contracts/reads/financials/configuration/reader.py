from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.configuration.models.setup_facts import (
    FinanceSetupCostCodeFact,
    FinanceSetupCostCodeQuery,
    FinanceSetupFacts,
    FinanceSetupRestrictionFact,
    FinanceSetupRestrictionQuery,
)


class FinanceSetupReader(Protocol):
    def get_setup(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
    ) -> FinanceSetupFacts | None: ...

    def list_cost_codes(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinanceSetupCostCodeQuery,
    ) -> FinancePageFacts[FinanceSetupCostCodeFact]: ...

    def list_restrictions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinanceSetupRestrictionQuery,
    ) -> FinancePageFacts[FinanceSetupRestrictionFact]: ...


__all__ = ["FinanceSetupReader"]
