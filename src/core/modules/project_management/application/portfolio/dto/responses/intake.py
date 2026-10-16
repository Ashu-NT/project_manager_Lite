from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.core.modules.project_management.domain.portfolio import PortfolioIntakeStatus


@dataclass(frozen=True, slots=True)
class PortfolioIntakeResponse:
    """Detached intake evidence with its canonical domain-calculated score."""

    id: str
    title: str
    sponsor_name: str
    organization_id: str
    summary: str
    requested_budget: Decimal
    requested_capacity_percent: float
    target_start_date: date | None
    strategic_score: int
    value_score: int
    urgency_score: int
    risk_score: int
    scoring_template_id: str
    scoring_template_name: str
    strategic_weight: int
    value_weight: int
    urgency_weight: int
    risk_weight: int
    status: PortfolioIntakeStatus
    created_at: datetime
    updated_at: datetime
    version: int
    composite_score: int


@dataclass(frozen=True, slots=True)
class PortfolioIntakePageResponse:
    items: tuple[PortfolioIntakeResponse, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "updatedAt"
    sort_direction: str = "desc"
    search_text: str = ""
    next_cursor: str | None = None
