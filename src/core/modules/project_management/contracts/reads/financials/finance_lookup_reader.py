from __future__ import annotations

from typing import Protocol

from .models.finance_lookup_facts import (
    FinanceLookupOptionFact,
    FinanceLookupPageFacts,
    FinanceLookupQuery,
    ManualActualCostCodeQuery,
    ManualActualDefaultsFacts,
)


class FinanceLookupReader(Protocol):
    def search_projects(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        require_active_finance_profile: bool,
        request: FinanceLookupQuery,
    ) -> FinanceLookupPageFacts: ...

    def get_project_option(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        require_active_finance_profile: bool,
    ) -> FinanceLookupOptionFact | None: ...

    def search_tasks(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinanceLookupQuery,
    ) -> FinanceLookupPageFacts: ...

    def get_task_option(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        task_id: str,
    ) -> FinanceLookupOptionFact | None: ...

    def search_eligible_risks(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinanceLookupQuery,
    ) -> FinanceLookupPageFacts: ...

    def get_eligible_risk_option(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        risk_id: str,
    ) -> FinanceLookupOptionFact | None: ...

    def search_cost_codes(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: ManualActualCostCodeQuery,
    ) -> FinanceLookupPageFacts: ...

    def get_cost_code_option(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cost_code_id: str,
        effective_on,
    ) -> FinanceLookupOptionFact | None: ...

    def get_manual_actual_defaults(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
    ) -> ManualActualDefaultsFacts | None: ...


__all__ = ["FinanceLookupReader"]
