"""Portfolio use-case commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.portfolio import PortfolioIntakeStatus


@dataclass(frozen=True)
class PortfolioDependencyCreateCommand:
    predecessor_project_id: str
    successor_project_id: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    summary: str = ""


@dataclass(frozen=True)
class PortfolioIntakeCreateCommand:
    title: str
    sponsor_name: str
    summary: str = ""
    requested_budget: Decimal = Decimal(0)
    requested_capacity_percent: float = 0.0
    target_start_date: date | None = None
    strategic_score: int = 3
    value_score: int = 3
    urgency_score: int = 3
    risk_score: int = 3
    scoring_template_id: str | None = None
    status: str = PortfolioIntakeStatus.PROPOSED.value


@dataclass(frozen=True)
class PortfolioScenarioCreateCommand:
    name: str
    budget_limit: Decimal | None = None
    capacity_limit_percent: float | None = None
    project_ids: tuple[str, ...] = ()
    intake_item_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class PortfolioTemplateCreateCommand:
    name: str
    summary: str = ""
    strategic_weight: int = 3
    value_weight: int = 2
    urgency_weight: int = 2
    risk_weight: int = 1
    activate: bool = False


__all__ = [
    "PortfolioDependencyCreateCommand",
    "PortfolioIntakeCreateCommand",
    "PortfolioScenarioCreateCommand",
    "PortfolioTemplateCreateCommand",
]
