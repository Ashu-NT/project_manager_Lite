from __future__ import annotations

from datetime import date
from typing import Protocol

from .models.finance_overview_facts import FinanceOverviewFacts


class FinanceOverviewReader(Protocol):
    def read_overview_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        as_of: date,
    ) -> FinanceOverviewFacts | None: ...


__all__ = ["FinanceOverviewReader"]
