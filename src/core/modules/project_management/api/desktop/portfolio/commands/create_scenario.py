from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PortfolioScenarioCreateCommand:
    name: str
    budget_limit: Decimal | None = None
    capacity_limit_percent: float | None = None
    project_ids: tuple[str, ...] = ()
    intake_item_ids: tuple[str, ...] = ()
    notes: str = ""


__all__ = ["PortfolioScenarioCreateCommand"]
