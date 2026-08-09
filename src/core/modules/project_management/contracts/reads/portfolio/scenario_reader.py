from __future__ import annotations

from typing import Protocol

from .models.scenario_facts import PortfolioScenarioFacts


class PortfolioScenarioReader(Protocol):
    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        scenario_ids: tuple[str, ...],
        accessible_project_ids: tuple[str, ...],
    ) -> PortfolioScenarioFacts: ...


__all__ = ["PortfolioScenarioReader"]
