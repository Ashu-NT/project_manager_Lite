from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    FinanceSnapshotFacts,
)


@dataclass(frozen=True, slots=True)
class HeatmapTaskFact:
    id: str
    project_id: str
    name: str
    parent_task_id: str | None
    wbs_code: str
    sort_order: int
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    status: str
    priority: int
    percent_complete: float
    actual_start: date | None
    actual_end: date | None
    deadline: date | None


@dataclass(frozen=True, slots=True)
class HeatmapDependencyFact:
    id: str
    project_id: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: str
    lag_days: int


@dataclass(frozen=True, slots=True)
class HeatmapAssignmentFact:
    task_id: str
    resource_id: str
    allocation_percent: float


@dataclass(frozen=True, slots=True)
class HeatmapResourceFact:
    id: str
    name: str
    capacity_percent: float
    is_active: bool


@dataclass(frozen=True, slots=True)
class HeatmapProjectFacts:
    project_id: str
    project_name: str
    project_status: str
    finance: FinanceSnapshotFacts
    tasks: tuple[HeatmapTaskFact, ...]
    dependencies: tuple[HeatmapDependencyFact, ...]
    assignments: tuple[HeatmapAssignmentFact, ...]


@dataclass(frozen=True, slots=True)
class PortfolioHeatmapFacts:
    tenant_id: str
    organization_id: str
    as_of: date
    projects: tuple[HeatmapProjectFacts, ...]
    resources: tuple[HeatmapResourceFact, ...]


__all__ = [name for name in globals() if name.endswith("Fact") or name.endswith("Facts")]
