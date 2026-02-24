from __future__ import annotations

from datetime import date
from typing import List, Optional

from core.interfaces import BaselineRepository, ProjectRepository
from core.models import CostType
from core.services.reporting.cost_policy import ReportingCostPolicyMixin
from core.services.reporting.models import CostBreakdownRow


class ReportingCostBreakdownMixin(ReportingCostPolicyMixin):
    _project_repo: ProjectRepository
    _baseline_repo: BaselineRepository

    def get_cost_breakdown(
        self,
        project_id: str,
        as_of: Optional[date] = None,
        baseline_id: Optional[str] = None,
    ) -> List[CostBreakdownRow]:
        """
        Planned vs actual by (cost type, currency) with one canonical labor policy.

        Planned:
        - CostItem.planned_amount
        - + ProjectResource planned labor (planned_hours x resolved rate)
        - + baseline fallback (only when no planned data exists)

        Actual:
        - CostItem.actual_amount up to as_of
        - + assignment-based labor actuals (hours_logged x resolved rate)
        """
        as_of = as_of or date.today()
        snapshot = self._build_cost_policy_snapshot(project_id=project_id, as_of=as_of)

        planned_map = dict(snapshot.planned_map)
        actual_map = dict(snapshot.actual_map)

        # Keep historical fallback behavior for projects with no explicit planning data.
        if not planned_map:
            if baseline_id:
                baseline = self._baseline_repo.get_baseline(baseline_id)
            else:
                baseline = self._baseline_repo.get_latest_for_project(project_id)
            baseline_tasks = self._baseline_repo.list_tasks(baseline.id) if baseline else []
            baseline_total = float(
                sum(float(getattr(bt, "baseline_planned_cost", 0.0) or 0.0) for bt in baseline_tasks)
            )
            if baseline_total > 0:
                self._add_bucket(
                    planned_map,
                    cost_type=CostType.OTHER,
                    currency=self._normalize_currency(snapshot.project_currency),
                    amount=baseline_total,
                )

        rows: List[CostBreakdownRow] = []
        keys = set(planned_map.keys()) | set(actual_map.keys())
        for (cost_type, currency) in sorted(
            keys,
            key=lambda x: (x[0].value if hasattr(x[0], "value") else str(x[0]), x[1]),
        ):
            rows.append(
                CostBreakdownRow(
                    cost_type=cost_type.value if hasattr(cost_type, "value") else str(cost_type),
                    currency=currency,
                    planned=float(planned_map.get((cost_type, currency), 0.0) or 0.0),
                    actual=float(actual_map.get((cost_type, currency), 0.0) or 0.0),
                )
            )
        return rows

