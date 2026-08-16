from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class PortfolioExecutiveRow:
    project_id: str
    project_name: str
    project_status: str
    late_tasks: int
    critical_tasks: int
    peak_utilization_percent: float
    cost_variance: Decimal
    pressure_score: int
    pressure_label: str


@dataclass
class PortfolioRecentAction:
    occurred_at: datetime
    project_name: str
    actor_username: str
    action_label: str
    summary: str


__all__ = ["PortfolioExecutiveRow", "PortfolioRecentAction"]
