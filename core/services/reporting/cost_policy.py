from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Tuple

from core.exceptions import NotFoundError
from core.interfaces import (
    CostRepository,
    ProjectRepository,
    ProjectResourceRepository,
    ResourceRepository,
)
from core.models import CostType
from core.services.reporting.models import CostSourceBreakdown, CostSourceRow

CostBucketKey = Tuple[CostType, str]


@dataclass
class CostPolicySnapshot:
    project_id: str
    project_currency: str | None
    budget: float
    planned_map: Dict[CostBucketKey, float]
    committed_map: Dict[CostBucketKey, float]
    actual_map: Dict[CostBucketKey, float]
    planned_labor_total: float
    actual_labor_total: float
    include_manual_labor_planned: bool
    include_manual_labor_committed: bool
    include_manual_labor_actual: bool


@dataclass(frozen=True)
class CostControlTotals:
    project_id: str
    project_currency: str | None
    budget: float
    planned: float
    committed: float
    actual: float
    exposure: float
    available: float | None


class ReportingCostPolicyMixin:
    _project_repo: ProjectRepository
    _cost_repo: CostRepository
    _project_resource_repo: ProjectResourceRepository
    _resource_repo: ResourceRepository

    def _normalize_currency(self, value: str | None, fallback: str | None = None) -> str:
        code = (value or "").strip().upper()
        if code:
            return code
        fb = (fallback or "").strip().upper()
        return fb or "-"

    def _add_bucket(
        self,
        target: Dict[CostBucketKey, float],
        *,
        cost_type: CostType,
        currency: str,
        amount: float,
    ) -> None:
        if amount <= 0.0:
            return
        key = (cost_type, currency)
        target[key] = float(target.get(key, 0.0) + amount)

    def _currency_in_scope(self, currency: str, project_currency: str | None) -> bool:
        if not project_currency:
            return True
        return currency.upper() == project_currency.upper()

    def _sum_bucket_map(
        self,
        values: Dict[CostBucketKey, float],
        project_currency: str | None,
    ) -> float:
        if not project_currency:
            return float(sum(float(v or 0.0) for v in values.values()))
        cur = project_currency.upper()
        return float(
            sum(float(v or 0.0) for (ct, c), v in values.items() if c.upper() == cur)
        )

    def _sum_bucket_for_type(
        self,
        values: Dict[CostBucketKey, float],
        *,
        cost_type: CostType,
        project_currency: str | None,
    ) -> float:
        total = 0.0
        for (ct, cur), amount in values.items():
            if ct != cost_type:
                continue
            if not self._currency_in_scope(cur, project_currency):
                continue
            total += float(amount or 0.0)
        return float(total)

    def _sum_bucket_excluding_type(
        self,
        values: Dict[CostBucketKey, float],
        *,
        excluded_type: CostType,
        project_currency: str | None,
    ) -> float:
        total = 0.0
        for (ct, cur), amount in values.items():
            if ct == excluded_type:
                continue
            if not self._currency_in_scope(cur, project_currency):
                continue
            total += float(amount or 0.0)
        return float(total)

    def _resolve_planned_labor_map(self, project_id: str, project_currency: str | None) -> Dict[str, float]:
        planned_labor_by_currency: Dict[str, float] = {}
        prs = self._project_resource_repo.list_by_project(project_id) or []
        for pr in prs:
            if not getattr(pr, "is_active", True):
                continue
            planned_hours = float(getattr(pr, "planned_hours", 0.0) or 0.0)
            if planned_hours <= 0:
                continue

            res = self._resource_repo.get(getattr(pr, "resource_id", ""))
            rate = (
                float(pr.hourly_rate)
                if getattr(pr, "hourly_rate", None) is not None
                else float(getattr(res, "hourly_rate", 0.0) or 0.0)
            )
            if rate <= 0.0:
                continue

            cur = self._normalize_currency(
                getattr(pr, "currency_code", None) or getattr(res, "currency_code", None),
                project_currency,
            )
            planned_labor_by_currency[cur] = float(
                planned_labor_by_currency.get(cur, 0.0) + (planned_hours * rate)
            )
        return planned_labor_by_currency

    def _resolve_actual_labor_map(self, project_id: str, project_currency: str | None) -> Dict[str, float]:
        actual_labor_by_currency: Dict[str, float] = {}
        for row in self.get_project_labor_details(project_id):
            total = float(getattr(row, "total_cost", 0.0) or 0.0)
            if total <= 0:
                continue
            cur = self._normalize_currency(getattr(row, "currency_code", None), project_currency)
            actual_labor_by_currency[cur] = float(actual_labor_by_currency.get(cur, 0.0) + total)
        return actual_labor_by_currency

    def _build_cost_policy_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostPolicySnapshot:
        as_of = as_of or date.today()
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        project_currency = (
            (getattr(project, "currency", None) or "").strip().upper() or None
        )
        budget = float(getattr(project, "planned_budget", 0.0) or 0.0)

        planned_labor_by_currency = self._resolve_planned_labor_map(project_id, project_currency)
        actual_labor_by_currency = self._resolve_actual_labor_map(project_id, project_currency)
        planned_labor_total = float(sum(planned_labor_by_currency.values()))
        actual_labor_total = float(sum(actual_labor_by_currency.values()))

        # Manual LABOR rows are fallback-only to avoid double counting when labor is
        # represented by project resource planning and/or assignment execution.
        include_manual_labor_planned = planned_labor_total <= 0.0
        include_manual_labor_actual = actual_labor_total <= 0.0
        include_manual_labor_committed = (
            include_manual_labor_planned and include_manual_labor_actual
        )

        planned_map: Dict[CostBucketKey, float] = {}
        committed_map: Dict[CostBucketKey, float] = {}
        actual_map: Dict[CostBucketKey, float] = {}

        for item in self._cost_repo.list_by_project(project_id):
            cost_type = getattr(item, "cost_type", None) or CostType.OTHER
            currency = self._normalize_currency(getattr(item, "currency_code", None), project_currency)

            planned_amount = float(getattr(item, "planned_amount", 0.0) or 0.0)
            if planned_amount > 0 and (cost_type != CostType.LABOR or include_manual_labor_planned):
                self._add_bucket(
                    planned_map,
                    cost_type=cost_type,
                    currency=currency,
                    amount=planned_amount,
                )

            committed_amount = float(getattr(item, "committed_amount", 0.0) or 0.0)
            if committed_amount > 0 and (cost_type != CostType.LABOR or include_manual_labor_committed):
                self._add_bucket(
                    committed_map,
                    cost_type=cost_type,
                    currency=currency,
                    amount=committed_amount,
                )

            actual_amount = float(getattr(item, "actual_amount", 0.0) or 0.0)
            if actual_amount > 0 and (cost_type != CostType.LABOR or include_manual_labor_actual):
                incurred = getattr(item, "incurred_date", None)
                if incurred is None or incurred <= as_of:
                    self._add_bucket(
                        actual_map,
                        cost_type=cost_type,
                        currency=currency,
                        amount=actual_amount,
                    )

        for currency, amount in planned_labor_by_currency.items():
            self._add_bucket(
                planned_map,
                cost_type=CostType.LABOR,
                currency=currency,
                amount=float(amount or 0.0),
            )

        for currency, amount in actual_labor_by_currency.items():
            self._add_bucket(
                actual_map,
                cost_type=CostType.LABOR,
                currency=currency,
                amount=float(amount or 0.0),
            )

        return CostPolicySnapshot(
            project_id=project_id,
            project_currency=project_currency,
            budget=budget,
            planned_map=planned_map,
            committed_map=committed_map,
            actual_map=actual_map,
            planned_labor_total=planned_labor_total,
            actual_labor_total=actual_labor_total,
            include_manual_labor_planned=include_manual_labor_planned,
            include_manual_labor_committed=include_manual_labor_committed,
            include_manual_labor_actual=include_manual_labor_actual,
        )

    def get_project_cost_control_totals(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostControlTotals:
        snapshot = self._build_cost_policy_snapshot(project_id, as_of=as_of)
        planned = self._sum_bucket_map(snapshot.planned_map, snapshot.project_currency)
        committed = self._sum_bucket_map(snapshot.committed_map, snapshot.project_currency)
        actual = self._sum_bucket_map(snapshot.actual_map, snapshot.project_currency)
        exposure = float(max(committed, actual))
        available = float(snapshot.budget - exposure) if snapshot.budget > 0 else None

        return CostControlTotals(
            project_id=project_id,
            project_currency=snapshot.project_currency,
            budget=float(snapshot.budget),
            planned=planned,
            committed=committed,
            actual=actual,
            exposure=exposure,
            available=available,
        )

    def get_project_cost_source_breakdown(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostSourceBreakdown:
        as_of = as_of or date.today()
        snapshot = self._build_cost_policy_snapshot(project_id, as_of=as_of)

        direct_planned = self._sum_bucket_excluding_type(
            snapshot.planned_map,
            excluded_type=CostType.LABOR,
            project_currency=snapshot.project_currency,
        )
        direct_committed = self._sum_bucket_excluding_type(
            snapshot.committed_map,
            excluded_type=CostType.LABOR,
            project_currency=snapshot.project_currency,
        )
        direct_actual = self._sum_bucket_excluding_type(
            snapshot.actual_map,
            excluded_type=CostType.LABOR,
            project_currency=snapshot.project_currency,
        )

        labor_planned_total = self._sum_bucket_for_type(
            snapshot.planned_map,
            cost_type=CostType.LABOR,
            project_currency=snapshot.project_currency,
        )
        labor_committed_total = self._sum_bucket_for_type(
            snapshot.committed_map,
            cost_type=CostType.LABOR,
            project_currency=snapshot.project_currency,
        )
        labor_actual_total = self._sum_bucket_for_type(
            snapshot.actual_map,
            cost_type=CostType.LABOR,
            project_currency=snapshot.project_currency,
        )

        manual_raw_planned = 0.0
        manual_raw_committed = 0.0
        manual_raw_actual = 0.0
        for item in self._cost_repo.list_by_project(project_id):
            if (getattr(item, "cost_type", None) or CostType.OTHER) != CostType.LABOR:
                continue
            cur = self._normalize_currency(getattr(item, "currency_code", None), snapshot.project_currency)
            if not self._currency_in_scope(cur, snapshot.project_currency):
                continue
            manual_raw_planned += float(getattr(item, "planned_amount", 0.0) or 0.0)
            manual_raw_committed += float(getattr(item, "committed_amount", 0.0) or 0.0)
            actual_amt = float(getattr(item, "actual_amount", 0.0) or 0.0)
            incurred = getattr(item, "incurred_date", None)
            if incurred is None or incurred <= as_of:
                manual_raw_actual += actual_amt

        manual_planned = manual_raw_planned if snapshot.include_manual_labor_planned else 0.0
        manual_actual = manual_raw_actual if snapshot.include_manual_labor_actual else 0.0

        computed_planned = max(0.0, float(labor_planned_total - manual_planned))
        computed_actual = max(0.0, float(labor_actual_total - manual_actual))

        rows = [
            CostSourceRow(
                source_key="DIRECT_COST",
                source_label="Direct Cost",
                planned=float(direct_planned),
                committed=float(direct_committed),
                actual=float(direct_actual),
            ),
            CostSourceRow(
                source_key="COMPUTED_LABOR",
                source_label="Computed Labor",
                planned=float(computed_planned),
                committed=0.0,
                actual=float(computed_actual),
            ),
            CostSourceRow(
                source_key="LABOR_ADJUSTMENT",
                source_label="Labor Adjustment",
                planned=float(manual_planned),
                committed=float(labor_committed_total),
                actual=float(manual_actual),
            ),
        ]

        notes: list[str] = []
        if manual_raw_planned > 0 or manual_raw_committed > 0 or manual_raw_actual > 0:
            if not (
                snapshot.include_manual_labor_planned
                and snapshot.include_manual_labor_committed
                and snapshot.include_manual_labor_actual
            ):
                notes.append(
                    "Manual labor adjustment entries are recorded, but excluded from "
                    "totals while computed labor exists."
                )
            else:
                notes.append("Manual labor adjustment entries are active in current totals.")

        return CostSourceBreakdown(
            project_id=project_id,
            project_currency=snapshot.project_currency,
            rows=rows,
            total_planned=float(direct_planned + computed_planned + manual_planned),
            total_committed=float(direct_committed + labor_committed_total),
            total_actual=float(direct_actual + computed_actual + manual_actual),
            notes=notes,
        )
