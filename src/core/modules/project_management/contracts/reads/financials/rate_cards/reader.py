from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.rate_cards.models.rate_facts import (
    RateCardFact,
    RateCardRequest,
    RateLineFact,
    RateLineRequest,
)


class FinanceRateReader(Protocol):
    def list_cards(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: RateCardRequest,
    ) -> FinancePageFacts[RateCardFact]: ...

    def get_card(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        rate_card_id: str,
    ) -> RateCardFact | None: ...

    def list_lines(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        rate_card_id: str,
        request: RateLineRequest,
    ) -> FinancePageFacts[RateLineFact]: ...


__all__ = ["FinanceRateReader"]
