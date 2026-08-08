from __future__ import annotations

from datetime import date
from typing import Protocol

from .models.heatmap_facts import PortfolioHeatmapFacts


class PortfolioHeatmapReader(Protocol):
    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_ids: tuple[str, ...],
        as_of: date,
    ) -> PortfolioHeatmapFacts: ...


__all__ = ["PortfolioHeatmapReader"]
