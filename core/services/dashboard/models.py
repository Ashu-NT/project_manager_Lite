from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from core.services.reporting.models import CostSourceBreakdown, ProjectKPI, ResourceLoadRow


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
class DashboardData:
    kpi: ProjectKPI
    resource_load: List[ResourceLoadRow]
    alerts: List[str]
    upcoming_tasks: List[UpcomingTask]
    burndown: List[BurndownPoint]
    cost_sources: CostSourceBreakdown | None = None
    evm: Optional[DashboardEVM] = None
