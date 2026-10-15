from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.invoicing.models.billing_facts import (
    AccountingStatusFact,
    AccountingStatusQuery,
    BillingPreparationDetailFact,
    BillingPreparationLineFact,
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingPreparationSummaryFact,
    BillingProfileFact,
    BillingScheduleFact,
    BillingScheduleQuery,
    BillingSourceOptionFact,
    BillingSourceQuery,
)


class FinanceBillingReader(Protocol):
    def list_eligible_sources(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        preparation_id: str,
        request: BillingSourceQuery,
    ) -> FinancePageFacts[BillingSourceOptionFact]: ...

    def approved_preparation_amount(
        self, *, tenant_id: str, organization_id: str, project_id: str
    ) -> Decimal: ...

    def list_accounting_statuses(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: AccountingStatusQuery,
    ) -> FinancePageFacts[AccountingStatusFact]: ...

    def get_profile(
        self, *, tenant_id: str, organization_id: str, project_id: str
    ) -> BillingProfileFact | None: ...

    def list_schedule(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: BillingScheduleQuery,
    ) -> FinancePageFacts[BillingScheduleFact]: ...

    def list_preparations(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: BillingPreparationQuery,
    ) -> FinancePageFacts[BillingPreparationSummaryFact]: ...

    def get_preparation(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        preparation_id: str,
    ) -> BillingPreparationDetailFact | None: ...

    def list_preparation_lines(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        preparation_id: str,
        request: BillingPreparationLineQuery,
    ) -> FinancePageFacts[BillingPreparationLineFact]: ...


__all__ = ["FinanceBillingReader"]
