"""Reporting capabilities consumed by dashboard orchestration."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from src.core.modules.project_management.application.dashboard.models.report_models import (
    ProjectKPI,
    ResourceLoadRow,
)
from src.core.modules.project_management.application.financials.models import (
    CostSourceBreakdown,
    EarnedValueMetrics,
)
from src.core.modules.project_management.application.scheduling.models.cpm import (
    CPMTaskInfo,
)


class DashboardReportingQuery(Protocol):
    def get_project_kpis(
        self, project_id: str, *, schedule: dict[str, CPMTaskInfo] | None = None,
        as_of: date | None = None,
    ) -> ProjectKPI: ...

    def get_resource_load_summary(self, project_id: str) -> list[ResourceLoadRow]: ...

    def get_earned_value(
        self, project_id: str, as_of: date | None = None, baseline_id: str | None = None,
    ) -> EarnedValueMetrics: ...

    def get_project_cost_source_breakdown(
        self, project_id: str, *, as_of: date | None = None,
    ) -> CostSourceBreakdown: ...
