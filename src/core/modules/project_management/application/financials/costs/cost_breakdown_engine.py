"""Cost breakdown engine — provides planned-vs-actual by (type, currency).

Delegates to CostPolicyEngine for consistent labor policy treatment.
Reporting delegates here rather than owning cost breakdown logic.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.application.financials.costs.cost_policy_engine import (
    CostPolicyEngine,
)

from src.core.modules.project_management.application.financials.models.finance_models import (
    CostBreakdownRow,
)


class CostBreakdownEngine:
    """
    Build cost breakdown rows (planned vs actual by cost type and currency).

    Uses CostPolicyEngine to ensure consistent labor policy treatment.
    When no planned data exists, falls back to baseline planned cost totals.
    """

    def __init__(
        self,
        *,
        baseline_repo: BaselineRepository,
        cost_policy_engine: CostPolicyEngine,
    ) -> None:
        self._baseline_repo = baseline_repo
        self._engine = cost_policy_engine

    def build_breakdown(
        self,
        project_id: str,
        *,
        as_of: Optional[date] = None,
        baseline_id: Optional[str] = None,
    ) -> List[CostBreakdownRow]:
        as_of = as_of or date.today()
        snapshot = self._engine.build_snapshot(project_id, as_of=as_of)

        planned_map = dict(snapshot.planned_map)
        actual_map = dict(snapshot.actual_map)

        # Historical fallback for projects with no explicit planning data.
        if not planned_map:
            if baseline_id:
                baseline = self._baseline_repo.get_baseline(baseline_id)
            else:
                baseline = self._baseline_repo.get_latest_for_project(project_id)
            baseline_tasks = self._baseline_repo.list_tasks(baseline.id) if baseline else []
            baseline_total = float(
                sum(
                    float(getattr(bt, "baseline_planned_cost", 0.0) or 0.0)
                    for bt in baseline_tasks
                )
            )
            if baseline_total > 0:
                self._engine._add_bucket(
                    planned_map,
                    cost_type=CostType.OTHER,
                    currency=self._engine._normalize_currency(snapshot.project_currency),
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


__all__ = ["CostBreakdownEngine"]
