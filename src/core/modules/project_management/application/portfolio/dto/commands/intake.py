from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.portfolio._command_values import (
    PORTFOLIO_UNSET,
)
from src.core.modules.project_management.domain.portfolio import PortfolioIntakeStatus


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
class PortfolioIntakeUpdateCommand:
    item_id: str
    title: str | None = None
    sponsor_name: str | None = None
    summary: str | None = None
    requested_budget: Decimal | int | str | None = None
    requested_capacity_percent: float | str | None = None
    target_start_date: date | None | object = PORTFOLIO_UNSET
    strategic_score: int | str | None = None
    value_score: int | str | None = None
    urgency_score: int | str | None = None
    risk_score: int | str | None = None
    status: PortfolioIntakeStatus | str | None = None
    scoring_template_id: str | None = None
