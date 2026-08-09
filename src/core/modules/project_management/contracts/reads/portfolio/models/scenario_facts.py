from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class PortfolioScenarioFact:
    id: str
    name: str
    budget_limit: float | None
    capacity_limit_percent: float | None
    project_ids: tuple[str, ...]
    intake_item_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioScenarioProjectFact:
    id: str
    name: str
    planned_budget: float


@dataclass(frozen=True, slots=True)
class PortfolioScenarioIntakeFact:
    id: str
    title: str
    requested_budget: float
    requested_capacity_percent: float
    composite_score: int


@dataclass(frozen=True, slots=True)
class PortfolioScenarioTaskFact:
    id: str
    project_id: str
    parent_task_id: str | None
    start_date: date | None
    end_date: date | None


@dataclass(frozen=True, slots=True)
class PortfolioScenarioAssignmentFact:
    task_id: str
    resource_id: str
    allocation_percent: float


@dataclass(frozen=True, slots=True)
class PortfolioScenarioResourceFact:
    id: str
    name: str
    capacity_percent: float
    is_active: bool


@dataclass(frozen=True, slots=True)
class PortfolioScenarioFacts:
    tenant_id: str
    organization_id: str
    scenarios: tuple[PortfolioScenarioFact, ...]
    projects: tuple[PortfolioScenarioProjectFact, ...]
    intake_items: tuple[PortfolioScenarioIntakeFact, ...]
    tasks: tuple[PortfolioScenarioTaskFact, ...]
    assignments: tuple[PortfolioScenarioAssignmentFact, ...]
    resources: tuple[PortfolioScenarioResourceFact, ...]


__all__ = [name for name in globals() if name.startswith("PortfolioScenario")]
