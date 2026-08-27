from __future__ import annotations

from typing import Protocol

from .models.finance_budget_facts import (
    BudgetLineFact,
    BudgetVersionFact,
    FinancePageFacts,
    FinancePageRequest,
)


class FinanceBudgetReader(Protocol):
    def list_versions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinancePageRequest,
    ) -> FinancePageFacts[BudgetVersionFact]: ...

    def list_lines(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        budget_id: str,
        request: FinancePageRequest,
    ) -> FinancePageFacts[BudgetLineFact]: ...


__all__ = ["FinanceBudgetReader"]
