from __future__ import annotations

from typing import Protocol

from .models.finance_performance_facts import CostPhasingFacts, CostPhasingQuery


class FinancePerformanceReader(Protocol):
    def read_cost_phasing(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        query: CostPhasingQuery,
    ) -> CostPhasingFacts | None: ...


__all__ = ["FinancePerformanceReader"]
