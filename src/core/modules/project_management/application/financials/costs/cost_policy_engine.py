"""Cost policy engine — owns all cost bucket and policy snapshot logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from typing import Callable

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.cost import CostRepository
from src.core.modules.project_management.contracts.repositories.rate_resolution import (
    LaborRateResolver,
    UnresolvedLaborRate,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    CostAggregateFact,
    FinanceSnapshotFacts,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService

from src.core.modules.project_management.application.financials.models.finance_models import (
    CostSourceBreakdown,
    CostSourceRow,
    LaborDetailsResult,
)
from src.core.modules.project_management.application.financials.utils.helpers import (
    is_effectively_equal,
)

CostBucketKey = tuple[CostType, str]


@dataclass
class CostPolicySnapshot:
    """Raw cost bucket data before policy application."""
    project_id: str
    project_currency: str | None
    budget: float
    planned_map: dict[CostBucketKey, float]
    committed_map: dict[CostBucketKey, float]
    actual_map: dict[CostBucketKey, float]
    planned_labor_total: float
    actual_labor_total: float
    include_manual_labor_planned: bool
    include_manual_labor_committed: bool
    include_manual_labor_actual: bool
    unresolved_labor_rates: tuple[UnresolvedLaborRate, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CostControlTotals:
    """Policy-applied totals for a project — the finance control layer."""
    project_id: str
    project_currency: str | None
    budget: float
    planned: float
    committed: float
    actual: float
    exposure: float
    available: float | None
    unresolved_labor_rates: tuple[UnresolvedLaborRate, ...] = ()


@dataclass(frozen=True)
class CostPolicyComposition:
    snapshot: CostPolicySnapshot
    totals: CostControlTotals
    source_breakdown: CostSourceBreakdown
    manual_labor_included: dict[str, bool]


class CostPolicyEngine:
    """
    Compute cost control totals and source breakdowns for a project.

    Applies the labor policy (computed vs manual) so that all cost views
    (KPI, EVM, cost breakdown, finance snapshot) use a consistent baseline.

    Parameters
    ----------
    rate_resolver:
        Required. Resolves planned-labor rates (from ``ProjectResource``
        planning data) via the ADR-PF-005 rate-card system.
    get_labor_details:
        Optional callable ``(project_id: str, as_of: date) ->
        LaborDetailsResult``. When provided, actual labor is aggregated
        from its rows and any unresolved resources are carried through to
        this snapshot's own ``unresolved_labor_rates``. Without it, actual
        labor defaults to zero (manual cost items only).
    """

    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        cost_repo: CostRepository,
        project_resource_repo: ProjectResourceRepository,
        resource_repo: ResourceRepository,
        rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
        get_labor_details: Callable[[str, date], LaborDetailsResult] | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._cost_repo = cost_repo
        self._project_resource_repo = project_resource_repo
        self._resource_repo = resource_repo
        self._rate_resolver = rate_resolver
        self._tenant_context_service = tenant_context_service
        self._get_labor_details = get_labor_details

    @classmethod
    def for_facts(
        cls,
        *,
        rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
    ) -> "CostPolicyEngine":
        """Build the policy engine for immutable facts without repository fallbacks."""
        return cls(
            project_repo=None,  # type: ignore[arg-type]
            cost_repo=None,  # type: ignore[arg-type]
            project_resource_repo=None,  # type: ignore[arg-type]
            resource_repo=None,  # type: ignore[arg-type]
            rate_resolver=rate_resolver,
            tenant_context_service=tenant_context_service,
        )

    # ── public interface ──────────────────────────────────────────────────────

    def _resolve_scope(self, project) -> tuple[str, str]:
        context = self._tenant_context_service.require_organization_context(
            operation_label="build cost policy snapshot"
        )
        if project.organization_id and project.organization_id != context.organization_id:
            raise BusinessRuleError(
                "Project does not belong to the active organization.",
                code="PROJECT_ORGANIZATION_MISMATCH",
            )
        assert context.organization_id is not None  # guaranteed by require_organization_context
        return context.tenant_id, context.organization_id

    def build_snapshot(
        self,
        project_id: str,
        *,
        as_of: date,
    ) -> CostPolicySnapshot:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        tenant_id, organization_id = self._resolve_scope(project)

        project_currency = (
            (getattr(project, "currency", None) or "").strip().upper() or None
        )
        budget = float(getattr(project, "planned_budget", 0.0) or 0.0)

        planned_labor_by_currency, planned_unresolved = self._resolve_planned_labor_map(
            project_id,
            project_currency,
            tenant_id=tenant_id,
            organization_id=organization_id,
            as_of=as_of,
        )
        actual_labor_by_currency, actual_unresolved = self._resolve_actual_labor_map(
            project_id, project_currency, as_of=as_of
        )
        planned_labor_total = float(sum(planned_labor_by_currency.values()))
        actual_labor_total = float(sum(actual_labor_by_currency.values()))
        unresolved_labor_rates = tuple(planned_unresolved) + tuple(actual_unresolved)

        # Manual LABOR rows are fallback-only to avoid double-counting.
        include_manual_labor_planned = planned_labor_total <= 0.0
        include_manual_labor_actual = actual_labor_total <= 0.0
        include_manual_labor_committed = (
            include_manual_labor_planned and include_manual_labor_actual
        )

        planned_map: dict[CostBucketKey, float] = {}
        committed_map: dict[CostBucketKey, float] = {}
        actual_map: dict[CostBucketKey, float] = {}

        for item in self._cost_repo.list_by_project(project_id):
            cost_type = getattr(item, "cost_type", None) or CostType.OTHER
            currency = self._normalize_currency(
                getattr(item, "currency_code", None), project_currency
            )

            planned_amount = float(getattr(item, "planned_amount", 0.0) or 0.0)
            if planned_amount > 0 and (
                cost_type != CostType.LABOR or include_manual_labor_planned
            ):
                self._add_bucket(
                    planned_map,
                    cost_type=cost_type,
                    currency=currency,
                    amount=planned_amount,
                )

            committed_amount = float(getattr(item, "committed_amount", 0.0) or 0.0)
            if committed_amount > 0 and (
                cost_type != CostType.LABOR or include_manual_labor_committed
            ):
                self._add_bucket(
                    committed_map,
                    cost_type=cost_type,
                    currency=currency,
                    amount=committed_amount,
                )

            actual_amount = float(getattr(item, "actual_amount", 0.0) or 0.0)
            if actual_amount > 0 and (
                cost_type != CostType.LABOR or include_manual_labor_actual
            ):
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
            unresolved_labor_rates=unresolved_labor_rates,
        )

    def compose_from_facts(
        self,
        facts: FinanceSnapshotFacts,
        labor_details: LaborDetailsResult,
    ) -> CostPolicyComposition:
        """Apply existing cost policy to reader facts and one labor result."""
        project_currency = self._normalize_currency(facts.project.currency, None)
        if project_currency == "-":
            project_currency = None

        planned_labor_by_currency: dict[str, float] = {}
        for row in labor_details.planned_rows:
            currency = self._normalize_currency(row.currency_code, project_currency)
            planned_labor_by_currency[currency] = float(
                planned_labor_by_currency.get(currency, 0.0) + row.total_cost
            )
        actual_labor_by_currency: dict[str, float] = {}
        for row in labor_details.rows:
            if row.total_cost <= 0.0:
                continue
            currency = self._normalize_currency(row.currency_code, project_currency)
            actual_labor_by_currency[currency] = float(
                actual_labor_by_currency.get(currency, 0.0) + row.total_cost
            )

        planned_labor_total = float(sum(planned_labor_by_currency.values()))
        actual_labor_total = float(sum(actual_labor_by_currency.values()))
        include_planned = planned_labor_total <= 0.0
        include_actual = actual_labor_total <= 0.0
        include_committed = include_planned and include_actual
        planned_map: dict[CostBucketKey, float] = {}
        committed_map: dict[CostBucketKey, float] = {}
        actual_map: dict[CostBucketKey, float] = {}
        manual_raw_all = {"planned": 0.0, "committed": 0.0, "actual": 0.0}
        manual_raw_in_scope = {"planned": 0.0, "committed": 0.0, "actual": 0.0}

        for aggregate in facts.cost_aggregates:
            try:
                cost_type = CostType(aggregate.cost_type)
            except ValueError:
                cost_type = CostType.OTHER
            currency = self._normalize_currency(aggregate.currency_code, project_currency)
            if cost_type == CostType.LABOR:
                manual_raw_all["planned"] += aggregate.raw_planned
                manual_raw_all["committed"] += aggregate.raw_committed
                manual_raw_all["actual"] += aggregate.raw_actual_as_of
                if self._currency_in_scope(currency, project_currency):
                    manual_raw_in_scope["planned"] += aggregate.raw_planned
                    manual_raw_in_scope["committed"] += aggregate.raw_committed
                    manual_raw_in_scope["actual"] += aggregate.raw_actual_as_of
            if cost_type != CostType.LABOR or include_planned:
                self._add_bucket(
                    planned_map,
                    cost_type=cost_type,
                    currency=currency,
                    amount=aggregate.positive_planned,
                )
            if cost_type != CostType.LABOR or include_committed:
                self._add_bucket(
                    committed_map,
                    cost_type=cost_type,
                    currency=currency,
                    amount=aggregate.positive_committed,
                )
            if cost_type != CostType.LABOR or include_actual:
                self._add_bucket(
                    actual_map,
                    cost_type=cost_type,
                    currency=currency,
                    amount=aggregate.positive_actual_as_of,
                )

        for currency, amount in planned_labor_by_currency.items():
            self._add_bucket(planned_map, cost_type=CostType.LABOR, currency=currency, amount=amount)
        for currency, amount in actual_labor_by_currency.items():
            self._add_bucket(actual_map, cost_type=CostType.LABOR, currency=currency, amount=amount)

        snapshot = CostPolicySnapshot(
            project_id=facts.project_id,
            project_currency=project_currency,
            budget=float(facts.project.planned_budget),
            planned_map=planned_map,
            committed_map=committed_map,
            actual_map=actual_map,
            planned_labor_total=planned_labor_total,
            actual_labor_total=actual_labor_total,
            include_manual_labor_planned=include_planned,
            include_manual_labor_committed=include_committed,
            include_manual_labor_actual=include_actual,
            unresolved_labor_rates=(
                tuple(labor_details.planned_unresolved_rates)
                + tuple(labor_details.unresolved_rates)
            ),
        )
        source_breakdown = self._source_breakdown_from_snapshot(
            snapshot,
            manual_raw=manual_raw_in_scope,
        )
        source_manual = next(
            row for row in source_breakdown.rows if row.source_key == "LABOR_ADJUSTMENT"
        )
        manual_included = {
            stage: (
                manual_raw_all[stage] <= 0.0
                or is_effectively_equal(
                    manual_raw_all[stage],
                    float(getattr(source_manual, stage)),
                )
            )
            for stage in ("planned", "committed", "actual")
        }
        return CostPolicyComposition(
            snapshot=snapshot,
            totals=self._totals_from_snapshot(snapshot),
            source_breakdown=source_breakdown,
            manual_labor_included=manual_included,
        )

    def compose_from_facts_at(
        self,
        facts: FinanceSnapshotFacts,
        labor_details: LaborDetailsResult,
        *,
        as_of: date,
    ) -> CostPolicyComposition:
        """Apply policy at one date without re-reading stored cost rows."""
        if as_of == facts.as_of:
            return self.compose_from_facts(facts, labor_details)
        return self.compose_from_facts(
            replace(
                facts,
                as_of=as_of,
                cost_aggregates=self._aggregate_cost_items_at(facts, as_of=as_of),
            ),
            labor_details,
        )

    @staticmethod
    def _aggregate_cost_items_at(
        facts: FinanceSnapshotFacts,
        *,
        as_of: date,
    ) -> tuple[CostAggregateFact, ...]:
        buckets: dict[tuple[str, str | None, str], list[float]] = {}
        for item in facts.cost_items:
            key = (item.cost_type, item.currency_code, item.commitment_status)
            values = buckets.setdefault(key, [0.0] * 7)
            values[0] += item.planned_amount if item.planned_amount > 0.0 else 0.0
            values[1] += item.committed_amount if item.committed_amount > 0.0 else 0.0
            actual_in_scope = item.incurred_date is None or item.incurred_date <= as_of
            if actual_in_scope and item.actual_amount > 0.0:
                values[2] += item.actual_amount
            values[3] += item.planned_amount
            values[4] += item.committed_amount
            if actual_in_scope:
                values[5] += item.actual_amount
            values[6] += 1.0
        return tuple(
            CostAggregateFact(
                cost_type=key[0],
                currency_code=key[1],
                commitment_status=key[2],
                positive_planned=values[0],
                positive_committed=values[1],
                positive_actual_as_of=values[2],
                raw_planned=values[3],
                raw_committed=values[4],
                raw_actual_as_of=values[5],
                row_count=int(values[6]),
            )
            for key, values in buckets.items()
        )

    def _totals_from_snapshot(self, snapshot: CostPolicySnapshot) -> CostControlTotals:
        planned = self._sum_bucket_map(snapshot.planned_map, snapshot.project_currency)
        committed = self._sum_bucket_map(snapshot.committed_map, snapshot.project_currency)
        actual = self._sum_bucket_map(snapshot.actual_map, snapshot.project_currency)
        exposure = float(max(committed, actual))
        return CostControlTotals(
            project_id=snapshot.project_id,
            project_currency=snapshot.project_currency,
            budget=float(snapshot.budget),
            planned=planned,
            committed=committed,
            actual=actual,
            exposure=exposure,
            available=(float(snapshot.budget - exposure) if snapshot.budget > 0 else None),
            unresolved_labor_rates=snapshot.unresolved_labor_rates,
        )

    def _source_breakdown_from_snapshot(
        self,
        snapshot: CostPolicySnapshot,
        *,
        manual_raw: dict[str, float],
    ) -> CostSourceBreakdown:
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

        manual_raw_planned = manual_raw["planned"]
        manual_raw_committed = manual_raw["committed"]
        manual_raw_actual = manual_raw["actual"]

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
            project_id=snapshot.project_id,
            project_currency=snapshot.project_currency,
            rows=rows,
            total_planned=float(direct_planned + computed_planned + manual_planned),
            total_committed=float(direct_committed + labor_committed_total),
            total_actual=float(direct_actual + computed_actual + manual_actual),
            notes=notes,
        )

    # ── internal helpers ──────────────────────────────────────────────────────

    def _normalize_currency(self, value: str | None, fallback: str | None = None) -> str:
        code = (value or "").strip().upper()
        if code:
            return code
        fb = (fallback or "").strip().upper()
        return fb or "-"

    def _add_bucket(
        self,
        target: dict[CostBucketKey, float],
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
        values: dict[CostBucketKey, float],
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
        values: dict[CostBucketKey, float],
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
        values: dict[CostBucketKey, float],
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

    def _resolve_planned_labor_map(
        self,
        project_id: str,
        project_currency: str | None,
        *,
        tenant_id: str,
        organization_id: str,
        as_of: date,
    ) -> tuple[dict[str, float], tuple[UnresolvedLaborRate, ...]]:
        planned_labor_by_currency: dict[str, float] = {}
        prs = self._project_resource_repo.list_by_project(project_id) or []
        active_prs = [
            pr
            for pr in prs
            if getattr(pr, "is_active", True)
            and float(getattr(pr, "planned_hours", 0.0) or 0.0) > 0
            and getattr(pr, "resource_id", None)
        ]
        resource_ids = tuple(str(pr.resource_id) for pr in active_prs)
        if not resource_ids:
            return planned_labor_by_currency, ()

        batch = self._rate_resolver.resolve_many(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            resource_ids=resource_ids,
            rate_type=RateType.COST,
            as_of=as_of,
            unit="HOUR",
        )
        for pr in active_prs:
            resource_id = str(pr.resource_id)
            snapshot = batch.snapshot_for(resource_id)
            if snapshot is None:
                continue  # excluded — recorded in batch.unresolved
            planned_hours = float(getattr(pr, "planned_hours", 0.0) or 0.0)
            rate = float(snapshot.monetary_rate.money.amount)
            cur = self._normalize_currency(
                snapshot.monetary_rate.money.currency.code, project_currency
            )
            planned_labor_by_currency[cur] = float(
                planned_labor_by_currency.get(cur, 0.0) + (planned_hours * rate)
            )
        return planned_labor_by_currency, batch.unresolved

    def _resolve_actual_labor_map(
        self,
        project_id: str,
        project_currency: str | None,
        *,
        as_of: date,
    ) -> tuple[dict[str, float], tuple[UnresolvedLaborRate, ...]]:
        actual_labor_by_currency: dict[str, float] = {}
        if self._get_labor_details is None:
            return actual_labor_by_currency, ()
        result = self._get_labor_details(project_id, as_of)
        for row in result.rows:
            total = float(getattr(row, "total_cost", 0.0) or 0.0)
            if total <= 0:
                continue
            cur = self._normalize_currency(
                getattr(row, "currency_code", None), project_currency
            )
            actual_labor_by_currency[cur] = float(
                actual_labor_by_currency.get(cur, 0.0) + total
            )
        return actual_labor_by_currency, result.unresolved_rates


__all__ = [
    "CostControlTotals",
    "CostPolicyComposition",
    "CostPolicyEngine",
    "CostPolicySnapshot",
]
