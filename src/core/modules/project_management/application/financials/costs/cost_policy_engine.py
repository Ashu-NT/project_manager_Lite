"""Canonical Project Finance cost-policy composition."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from src.core.modules.project_management.application.financials.models.finance_models import (
    CostSourceBreakdown,
    CostSourceRow,
    LaborDetailsResult,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    CostAggregateFact,
    FinanceLedgerFact,
    FinanceSnapshotFacts,
)
from src.core.modules.project_management.contracts.repositories.rate_resolution import (
    UnresolvedLaborRate,
)
from src.core.modules.project_management.domain.enums import CostType

CostBucketKey = tuple[CostType, str]


@dataclass
class CostPolicySnapshot:
    project_id: str
    project_currency: str | None
    budget: float
    planned_map: dict[CostBucketKey, float]
    committed_map: dict[CostBucketKey, float]
    actual_map: dict[CostBucketKey, float]
    unresolved_labor_rates: tuple[UnresolvedLaborRate, ...] = field(default_factory=tuple)


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
    unresolved_labor_rates: tuple[UnresolvedLaborRate, ...] = ()


@dataclass(frozen=True)
class CostPolicyComposition:
    snapshot: CostPolicySnapshot
    totals: CostControlTotals
    source_breakdown: CostSourceBreakdown


class CostPolicyEngine:
    """Compose financial control totals exclusively from canonical facts."""

    @classmethod
    def for_facts(cls, **_dependencies: object) -> "CostPolicyEngine":
        return cls()

    def compose_from_facts(
        self,
        facts: FinanceSnapshotFacts,
        labor_details: LaborDetailsResult | None = None,
    ) -> CostPolicyComposition:
        project_currency = self._normalize_currency(facts.project.currency_code, None)
        if project_currency == "-":
            project_currency = None
        maps: dict[str, dict[CostBucketKey, float]] = {
            "planned": {},
            "committed": {},
            "actual": {},
        }
        for aggregate in facts.cost_aggregates:
            if aggregate.stage not in maps:
                continue
            try:
                cost_type = CostType(aggregate.cost_type)
            except ValueError:
                cost_type = CostType.OTHER
            self._add_bucket(
                maps[aggregate.stage],
                cost_type=cost_type,
                currency=self._normalize_currency(
                    aggregate.currency_code, project_currency
                ),
                amount=aggregate.total_amount,
            )
        unresolved = ()
        if labor_details is not None:
            unresolved = (
                tuple(labor_details.planned_unresolved_rates)
                + tuple(labor_details.unresolved_rates)
            )
        snapshot = CostPolicySnapshot(
            project_id=facts.project_id,
            project_currency=project_currency,
            budget=float(facts.project.approved_budget),
            planned_map=maps["planned"],
            committed_map=maps["committed"],
            actual_map=maps["actual"],
            unresolved_labor_rates=unresolved,
        )
        return CostPolicyComposition(
            snapshot=snapshot,
            totals=self._totals_from_snapshot(snapshot),
            source_breakdown=self._source_breakdown_from_facts(
                facts, project_currency=project_currency
            ),
        )

    def compose_from_facts_at(
        self,
        facts: FinanceSnapshotFacts,
        labor_details: LaborDetailsResult | None = None,
        *,
        as_of: date,
    ) -> CostPolicyComposition:
        if as_of == facts.as_of:
            return self.compose_from_facts(facts, labor_details)
        entries = tuple(
            entry
            for entry in facts.ledger_entries
            if entry.occurred_on is None or entry.occurred_on <= as_of
        )
        return self.compose_from_facts(
            replace(
                facts,
                as_of=as_of,
                ledger_entries=entries,
                cost_aggregates=self._aggregate_entries(entries),
            ),
            labor_details,
        )

    @staticmethod
    def _aggregate_entries(
        entries: tuple[FinanceLedgerFact, ...],
    ) -> tuple[CostAggregateFact, ...]:
        buckets: dict[tuple[str, str, str | None], tuple[float, int]] = {}
        for entry in entries:
            key = (entry.stage, entry.cost_type, entry.currency_code)
            amount, count = buckets.get(key, (0.0, 0))
            buckets[key] = (amount + entry.amount, count + 1)
        return tuple(
            CostAggregateFact(
                stage=stage,
                cost_type=cost_type,
                currency_code=currency,
                total_amount=amount,
                row_count=count,
            )
            for (stage, cost_type, currency), (amount, count) in buckets.items()
        )

    def _totals_from_snapshot(self, snapshot: CostPolicySnapshot) -> CostControlTotals:
        planned = self._sum_bucket_map(snapshot.planned_map, snapshot.project_currency)
        committed = self._sum_bucket_map(snapshot.committed_map, snapshot.project_currency)
        actual = self._sum_bucket_map(snapshot.actual_map, snapshot.project_currency)
        exposure = max(0.0, committed - actual)
        return CostControlTotals(
            project_id=snapshot.project_id,
            project_currency=snapshot.project_currency,
            budget=snapshot.budget,
            planned=planned,
            committed=committed,
            actual=actual,
            exposure=exposure,
            available=(snapshot.budget - exposure if snapshot.budget > 0 else None),
            unresolved_labor_rates=snapshot.unresolved_labor_rates,
        )

    def _source_breakdown_from_facts(
        self,
        facts: FinanceSnapshotFacts,
        *,
        project_currency: str | None,
    ) -> CostSourceBreakdown:
        grouped: dict[str, CostSourceRow] = {}
        for entry in facts.ledger_entries:
            currency = self._normalize_currency(entry.currency_code, project_currency)
            if not self._currency_in_scope(currency, project_currency):
                continue
            row = grouped.setdefault(
                entry.source_key,
                CostSourceRow(
                    source_key=entry.source_key,
                    source_label=entry.source_label,
                    planned=0.0,
                    committed=0.0,
                    actual=0.0,
                ),
            )
            if entry.stage in {"planned", "committed", "actual"}:
                setattr(row, entry.stage, getattr(row, entry.stage) + entry.amount)
        rows = sorted(grouped.values(), key=lambda row: row.source_label.lower())
        return CostSourceBreakdown(
            project_id=facts.project_id,
            project_currency=project_currency,
            rows=rows,
            total_planned=sum(row.planned for row in rows),
            total_committed=sum(row.committed for row in rows),
            total_actual=sum(row.actual for row in rows),
            notes=[
                "Totals use versioned planned costs, Procurement commitments, and posted actual entries."
            ],
        )

    @staticmethod
    def _normalize_currency(value: str | None, fallback: str | None = None) -> str:
        return (value or fallback or "-").strip().upper() or "-"

    @staticmethod
    def _add_bucket(
        target: dict[CostBucketKey, float],
        *,
        cost_type: CostType,
        currency: str,
        amount: float,
    ) -> None:
        key = (cost_type, currency)
        target[key] = float(target.get(key, 0.0) + float(amount or 0.0))

    @staticmethod
    def _currency_in_scope(currency: str, project_currency: str | None) -> bool:
        return project_currency is None or currency.upper() == project_currency.upper()

    def _sum_bucket_map(
        self, values: dict[CostBucketKey, float], project_currency: str | None
    ) -> float:
        return float(
            sum(
                amount
                for (_cost_type, currency), amount in values.items()
                if self._currency_in_scope(currency, project_currency)
            )
        )

    def _sum_bucket_for_type(
        self,
        values: dict[CostBucketKey, float],
        *,
        cost_type: CostType,
        project_currency: str | None,
    ) -> float:
        return float(
            sum(
                amount
                for (candidate, currency), amount in values.items()
                if candidate == cost_type
                and self._currency_in_scope(currency, project_currency)
            )
        )

    def _sum_bucket_excluding_type(
        self,
        values: dict[CostBucketKey, float],
        *,
        excluded_type: CostType,
        project_currency: str | None,
    ) -> float:
        return float(
            sum(
                amount
                for (candidate, currency), amount in values.items()
                if candidate != excluded_type
                and self._currency_in_scope(currency, project_currency)
            )
        )


__all__ = [
    "CostControlTotals",
    "CostPolicyComposition",
    "CostPolicyEngine",
    "CostPolicySnapshot",
]
