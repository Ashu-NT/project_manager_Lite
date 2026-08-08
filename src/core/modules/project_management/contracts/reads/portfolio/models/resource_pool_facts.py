from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class PortfolioResourceFact:
    resource_id: str
    name: str
    capacity_percent: float


@dataclass(frozen=True, slots=True)
class PortfolioDemandFact:
    resource_id: str
    task_id: str
    project_id: str
    project_name: str
    start_date: date
    end_date: date
    allocation_percent: float


@dataclass(frozen=True, slots=True)
class PortfolioResourcePoolFacts:
    tenant_id: str
    organization_id: str
    resources: tuple[PortfolioResourceFact, ...]
    demands: tuple[PortfolioDemandFact, ...]


__all__ = [
    "PortfolioDemandFact",
    "PortfolioResourceFact",
    "PortfolioResourcePoolFacts",
]
