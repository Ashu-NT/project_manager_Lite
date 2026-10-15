from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.reads.financials.integration.models.integration_facts import (
    ApprovedTimePostingFailurePage,
    ApprovedTimePostingFailureQuery,
)


class FinanceIntegrationReader(Protocol):
    def list_approved_time_failures(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: ApprovedTimePostingFailureQuery,
    ) -> ApprovedTimePostingFailurePage: ...


__all__ = ["FinanceIntegrationReader"]
