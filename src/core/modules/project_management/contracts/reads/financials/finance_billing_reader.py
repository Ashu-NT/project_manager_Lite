from __future__ import annotations

from typing import Protocol

from .models.finance_billing_facts import (
    BillingPreparationDetailFact,
    BillingPreparationLineFact,
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingPreparationSummaryFact,
    BillingProfileFact,
    BillingScheduleFact,
    BillingScheduleQuery,
)
from .models.finance_budget_facts import FinancePageFacts


class FinanceBillingReader(Protocol):
    def get_profile(self, *, tenant_id: str, organization_id: str, project_id: str) -> BillingProfileFact | None: ...

    def list_schedule(self, *, tenant_id: str, organization_id: str, project_id: str, request: BillingScheduleQuery) -> FinancePageFacts[BillingScheduleFact]: ...

    def list_preparations(self, *, tenant_id: str, organization_id: str, project_id: str, request: BillingPreparationQuery) -> FinancePageFacts[BillingPreparationSummaryFact]: ...

    def get_preparation(self, *, tenant_id: str, organization_id: str, project_id: str, preparation_id: str) -> BillingPreparationDetailFact | None: ...

    def list_preparation_lines(self, *, tenant_id: str, organization_id: str, project_id: str, preparation_id: str, request: BillingPreparationLineQuery) -> FinancePageFacts[BillingPreparationLineFact]: ...


__all__ = ["FinanceBillingReader"]
