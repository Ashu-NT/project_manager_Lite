from __future__ import annotations

from datetime import date
from typing import Protocol

from .models.resource_pool_facts import PortfolioResourcePoolFacts


class PortfolioResourcePoolReader(Protocol):
    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        from_date: date,
        to_date: date,
        resource_ids: tuple[str, ...] | None = None,
    ) -> PortfolioResourcePoolFacts: ...


__all__ = ["PortfolioResourcePoolReader"]
