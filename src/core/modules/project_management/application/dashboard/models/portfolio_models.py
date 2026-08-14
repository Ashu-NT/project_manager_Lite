from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


PORTFOLIO_SCOPE_ID = "__portfolio__"


@dataclass
class PortfolioProjectRow:
    project_id: str
    project_name: str
    project_status: str
    progress_percent: float
    late_tasks: int
    critical_tasks: int
    cost_variance: Decimal
    risk_score: float


@dataclass
class PortfolioStatusRollupRow:
    status_label: str
    project_count: int


@dataclass
class DashboardPortfolio:
    projects_total: int
    active_projects: int
    completed_projects: int
    on_hold_projects: int
    at_risk_projects: int
    status_rollup: list[PortfolioStatusRollupRow]
    project_rankings: list[PortfolioProjectRow]


__all__ = [
    "PORTFOLIO_SCOPE_ID",
    "DashboardPortfolio",
    "PortfolioProjectRow",
    "PortfolioStatusRollupRow",
]
