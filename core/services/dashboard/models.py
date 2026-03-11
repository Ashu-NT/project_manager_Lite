from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from core.services.reporting.models import CostSourceBreakdown, ProjectKPI, ResourceLoadRow
from core.services.dashboard.portfolio_models import DashboardPortfolio
from core.services.register.models import RegisterProjectSummary


@dataclass
class DashboardEVM:
    as_of: date
    baseline_id: str
    BAC: float
    PV: float
    EV: float
    AC: float
    CPI: Optional[float]
    SPI: Optional[float]
    EAC: Optional[float]
    VAC: Optional[float]
    status_text: str
    TCPI_to_BAC: Optional[float]
    TCPI_to_EAC: Optional[float]


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
    resource_load: List[ResourceLoadRow]
    alerts: List[str]
    upcoming_tasks: List[UpcomingTask]
    burndown: List[BurndownPoint]
    milestone_health: list[MilestoneHealthRow] = field(default_factory=list)
    critical_watchlist: list[CriticalPathRow] = field(default_factory=list)
    register_summary: RegisterProjectSummary | None = None
    cost_sources: CostSourceBreakdown | None = None
    evm: Optional[DashboardEVM] = None
    portfolio: DashboardPortfolio | None = None
