from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PortfolioIntakeDesktopDto:
    id: str
    title: str
    sponsor_name: str
    summary: str
    requested_budget: float
    requested_budget_label: str
    requested_capacity_percent: float
    requested_capacity_label: str
    target_start_date: date | None
    target_start_date_label: str
    status: str
    status_label: str
    scoring_template_id: str
    scoring_template_name: str
    composite_score: int
    version: int


__all__ = ["PortfolioIntakeDesktopDto"]
