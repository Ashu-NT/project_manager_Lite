from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioScenarioCreateCommand:
    name: str
    budget_limit: float | None = None
    capacity_limit_percent: float | None = None
    project_ids: tuple[str, ...] = ()
    intake_item_ids: tuple[str, ...] = ()
    notes: str = ""


__all__ = ["PortfolioScenarioCreateCommand"]
