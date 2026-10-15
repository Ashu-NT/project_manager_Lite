from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.modules.project_management.application.portfolio._command_values import (
    PORTFOLIO_UNSET,
)


@dataclass(frozen=True)
class PortfolioScenarioCreateCommand:
    name: str
    budget_limit: Decimal | None = None
    capacity_limit_percent: float | None = None
    project_ids: tuple[str, ...] = ()
    intake_item_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class PortfolioScenarioUpdateCommand:
    scenario_id: str
    name: str | None = None
    budget_limit: Decimal | int | str | None | object = PORTFOLIO_UNSET
    capacity_limit_percent: float | str | None | object = PORTFOLIO_UNSET
    project_ids: tuple[str, ...] | None = None
    intake_item_ids: tuple[str, ...] | None = None
    notes: str | None = None
