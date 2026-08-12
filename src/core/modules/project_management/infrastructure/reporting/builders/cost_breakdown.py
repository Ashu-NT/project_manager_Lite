"""Cost breakdown mixin — thin reporting delegate.

Business logic lives in financials/costs/cost_breakdown_engine.py.
"""

from __future__ import annotations

from datetime import date

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
    def get_cost_breakdown(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> list[CostBreakdownRow]:
        self._require_finance_view("view cost breakdown report", project_id=project_id)
        resolved_as_of = as_of or date.today()
        facts, policy = self._compose_evm_policy(
            project_id,
            baseline_id=baseline_id,
            as_of=resolved_as_of,
        )
        engine = CostBreakdownEngine(
            cost_policy_engine=self._make_cost_policy_engine(),
        )
        return engine.build_breakdown_from_snapshot(
            policy.snapshot,
            baseline_tasks=facts.baseline_tasks,
        )
