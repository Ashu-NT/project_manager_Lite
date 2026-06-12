"""Cost breakdown mixin — thin reporting delegate.

Business logic lives in financials/costs/cost_breakdown_engine.py.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.modules.project_management.application.financials.costs.cost_breakdown_engine import (
    CostBreakdownEngine,
)
from src.core.modules.project_management.infrastructure.reporting.builders.cost_policy import (
    ReportingCostPolicyMixin,
)
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    CostBreakdownRow,
)

class ReportingCostBreakdownMixin(ReportingCostPolicyMixin):
    _project_repo: ProjectRepository
    _baseline_repo: BaselineRepository

    def get_cost_breakdown(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> list[CostBreakdownRow]:
        self._require_view("view cost breakdown report", project_id=project_id)
        engine = CostBreakdownEngine(
            baseline_repo=self._baseline_repo,
            cost_policy_engine=self._make_cost_policy_engine(),
        )
        return engine.build_breakdown(project_id, as_of=as_of, baseline_id=baseline_id)
