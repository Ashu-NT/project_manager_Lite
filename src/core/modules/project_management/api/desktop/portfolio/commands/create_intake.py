from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from src.core.modules.project_management.domain.portfolio import PortfolioIntakeStatus


@dataclass(frozen=True)
class PortfolioIntakeCreateCommand:
    title: str
    sponsor_name: str
    summary: str = ""
    requested_budget: float = 0.0
    requested_capacity_percent: float = 0.0
    target_start_date: date | None = None
    strategic_score: int = 3
    value_score: int = 3
    urgency_score: int = 3
    risk_score: int = 3
    scoring_template_id: str | None = None
    status: str = PortfolioIntakeStatus.PROPOSED.value


__all__ = ["PortfolioIntakeCreateCommand"]
