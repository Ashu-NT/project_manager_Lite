"""Dashboard DTOs — main project dashboard data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.core.modules.project_management.application.dashboard.models.portfolio_models import (
    DashboardPortfolio,
)
from src.core.modules.project_management.infrastructure.reporting import (
    CostSourceBreakdown,
    ProjectKPI,
    ResourceLoadRow,
)
from src.core.modules.project_management.application.risk import RegisterProjectSummary


@dataclass
class DashboardEVM:
    as_of: date
    baseline_id: str
    BAC: float
    PV: float
    EV: float
    AC: float
    CPI: float | None
    SPI: float | None
    EAC: float | None
    VAC: float | None
    status_text: str
    TCPI_to_BAC: float | None
    TCPI_to_EAC: float | None


@dataclass
class UpcomingTask:
    task_id: str
    name: str
    start_date: date | None
    end_date: date | None
    percent_complete: float
    main_resource: str | None
    is_late: bool
    is_critical: bool


@dataclass
class BurndownPoint:
    day: date
    remaining_tasks: int


@dataclass
class MilestoneHealthRow:
    task_id: str
    task_name: str
    owner_name: str | None
    target_date: date | None
    status_label: str
    slip_days: int | None


@dataclass
class CriticalPathRow:
    task_id: str
    task_name: str
    owner_name: str | None
    finish_date: date | None
    total_float_days: int | None
    late_by_days: int | None
    status_label: str


@dataclass
class DashboardData:
    kpi: ProjectKPI
    resource_load: list[ResourceLoadRow]
    alerts: list[str]
    upcoming_tasks: list[UpcomingTask]
    burndown: list[BurndownPoint]
    milestone_health: list[MilestoneHealthRow] = field(default_factory=list)
    critical_watchlist: list[CriticalPathRow] = field(default_factory=list)
    register_summary: RegisterProjectSummary | None = None
    cost_sources: CostSourceBreakdown | None = None
    evm: DashboardEVM | None = None
    portfolio: DashboardPortfolio | None = None


__all__ = [
    "BurndownPoint",
    "CriticalPathRow",
    "DashboardData",
    "DashboardEVM",
    "MilestoneHealthRow",
    "UpcomingTask",
]
