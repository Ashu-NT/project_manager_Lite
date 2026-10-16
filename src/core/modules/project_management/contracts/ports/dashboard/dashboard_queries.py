from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from src.core.modules.project_management.application.dashboard.models.report_models import (
    ProjectKPI,
    ResourceLoadRow,
)
from src.core.modules.project_management.application.financials.cost.dto.responses.cost_breakdown import (
    CostSourceBreakdown,
)
from src.core.modules.project_management.application.financials.earned_value.dto.responses.earned_value import (
    EarnedValueMetrics,
)
from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.application.resources.dto.responses.catalog import (
    ResourceResponse,
)
from src.core.modules.project_management.application.scheduling.models.cpm import (
    CPMTaskInfo,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment


class DashboardKpiQuery(Protocol):
    def get_project_kpis(
        self, project_id: str, *, schedule: dict[str, CPMTaskInfo] | None = None,
        as_of: date | None = None,
    ) -> ProjectKPI: ...

    def get_resource_load_summary(self, project_id: str) -> list[ResourceLoadRow]: ...


class DashboardEarnedValueQuery(Protocol):
    def get_earned_value(
        self, project_id: str, as_of: date | None = None, baseline_id: str | None = None,
    ) -> EarnedValueMetrics: ...


class DashboardCostSourceQuery(Protocol):
    def get_project_cost_source_breakdown(
        self, project_id: str, *, as_of: date | None = None,
    ) -> CostSourceBreakdown: ...


class DashboardTaskQuery(Protocol):
    def list_tasks_for_project(self, project_id: str) -> list[Task]: ...

    def list_assignments_for_tasks(self, task_ids: list[str]) -> list[TaskAssignment]: ...


class DashboardResourceQuery(Protocol):
    def list_resources(self) -> list[ResourceResponse]: ...


class DashboardProjectQuery(Protocol):
    def list_projects(self) -> Sequence[ProjectResponse]: ...


class DashboardScheduleQuery(Protocol):
    def recalculate_project_schedule(
        self, project_id: str, *, persist: bool = ...,
    ) -> dict[str, CPMTaskInfo]: ...


__all__ = ["DashboardCostSourceQuery", "DashboardEarnedValueQuery", "DashboardKpiQuery", "DashboardProjectQuery", "DashboardResourceQuery", "DashboardScheduleQuery", "DashboardTaskQuery"]
