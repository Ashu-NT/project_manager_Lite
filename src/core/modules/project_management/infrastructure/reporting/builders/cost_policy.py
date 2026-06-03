"""Cost policy mixin — thin reporting delegate.

Business logic lives in financials/costs/cost_policy_engine.py.
This mixin wires the reporting service's repos into CostPolicyEngine
so that all cost-policy calculations use a single authoritative implementation.
"""

from __future__ import annotations

from typing import Dict, Tuple

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.application.financials.costs.cost_policy_engine import (
    CostControlTotals,
    CostPolicyEngine,
    CostPolicySnapshot,
)

# Re-export so existing imports of these from reporting.builders.cost_policy still work.
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    CostSourceBreakdown,
    CostSourceRow,
)

CostBucketKey = Tuple[CostType, str]


class ReportingCostPolicyMixin:
    """Thin delegate — all logic lives in CostPolicyEngine (financials)."""

    def _make_cost_policy_engine(self) -> CostPolicyEngine:
        return CostPolicyEngine(
            project_repo=self._project_repo,
            cost_repo=self._cost_repo,
            project_resource_repo=self._project_resource_repo,
            resource_repo=self._resource_repo,
            get_labor_details=self.get_project_labor_details
            if hasattr(self, "get_project_labor_details")
            else None,
        )

    def _build_cost_policy_snapshot(
        self,
        project_id: str,
        *,
        as_of=None,
    ) -> CostPolicySnapshot:
        return self._make_cost_policy_engine().build_snapshot(project_id, as_of=as_of)

    def get_project_cost_control_totals(
        self,
        project_id: str,
        *,
        as_of=None,
    ) -> CostControlTotals:
        self._require_view("view cost control totals", project_id=project_id)
        return self._make_cost_policy_engine().get_cost_control_totals(project_id, as_of=as_of)

    def get_project_cost_source_breakdown(
        self,
        project_id: str,
        *,
        as_of=None,
    ) -> CostSourceBreakdown:
        self._require_view("view cost source breakdown", project_id=project_id)
        return self._make_cost_policy_engine().get_cost_source_breakdown(project_id, as_of=as_of)

    # Proxy helpers for mixins that call self._xxx() ─────────────────────────

    def _normalize_currency(self, value: str | None, fallback: str | None = None) -> str:
        return self._make_cost_policy_engine()._normalize_currency(value, fallback)

    def _add_bucket(
        self,
        target: Dict[CostBucketKey, float],
        *,
        cost_type: CostType,
        currency: str,
        amount: float,
    ) -> None:
        self._make_cost_policy_engine()._add_bucket(
            target, cost_type=cost_type, currency=currency, amount=amount
        )

    def _sum_bucket_map(
        self,
        values: Dict[CostBucketKey, float],
        project_currency: str | None,
    ) -> float:
        return self._make_cost_policy_engine()._sum_bucket_map(values, project_currency)

    def _sum_bucket_for_type(
        self,
        values: Dict[CostBucketKey, float],
        *,
        cost_type: CostType,
        project_currency: str | None,
    ) -> float:
        return self._make_cost_policy_engine()._sum_bucket_for_type(
            values, cost_type=cost_type, project_currency=project_currency
        )

    def _sum_bucket_excluding_type(
        self,
        values: Dict[CostBucketKey, float],
        *,
        excluded_type: CostType,
        project_currency: str | None,
    ) -> float:
        return self._make_cost_policy_engine()._sum_bucket_excluding_type(
            values, excluded_type=excluded_type, project_currency=project_currency
        )
