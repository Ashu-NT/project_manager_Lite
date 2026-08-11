"""Canonical Project Finance cost-policy composition."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal

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
    budget: Decimal
    planned_map: dict[CostBucketKey, Decimal]
    committed_map: dict[CostBucketKey, Decimal]
    actual_map: dict[CostBucketKey, Decimal]
    unresolved_labor_rates: tuple[UnresolvedLaborRate, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CostControlTotals:
    project_id: str
    project_currency: str | None
    budget: Decimal
    planned: Decimal
    committed: Decimal
    actual: Decimal
    forecast_etc: Decimal | None
    estimate_at_completion: Decimal | None
    variance_at_completion: Decimal | None
    exposure: Decimal
    available: Decimal | None
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
        maps: dict[str, dict[CostBucketKey, Decimal]] = {
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
            budget=facts.control.approved_budget,
            planned_map=maps["planned"],
            committed_map=maps["committed"],
            actual_map=maps["actual"],
            unresolved_labor_rates=unresolved,
        )
        return CostPolicyComposition(
            snapshot=snapshot,
            totals=self._totals_from_snapshot(snapshot, facts=facts),
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
        forecast = facts.approved_forecast
        if forecast is not None and forecast.as_of_date > as_of:
            forecast = None
        actual = self._sum_stage(entries, "actual")
        committed = self._sum_stage(entries, "committed")
        forecast_etc = self._sum_stage(entries, "forecast") if forecast else None
        return self.compose_from_facts(
            replace(
                facts,
                as_of=as_of,
                approved_forecast=forecast,
                control=replace(
                    facts.control,
                    posted_actual=actual,
                    open_commitment=committed,
                    forecast_etc=forecast_etc,
                ),
                ledger_entries=entries,
                cost_aggregates=self._aggregate_entries(entries),
            ),
            labor_details,
        )

    @staticmethod
    def _aggregate_entries(
        entries: tuple[FinanceLedgerFact, ...],
    ) -> tuple[CostAggregateFact, ...]:
        buckets: dict[tuple[str, str, str | None], tuple[Decimal, int]] = {}
        for entry in entries:
            key = (entry.stage, entry.cost_type, entry.currency_code)
            amount, count = buckets.get(key, (Decimal("0"), 0))
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

    def _totals_from_snapshot(
        self, snapshot: CostPolicySnapshot, *, facts: FinanceSnapshotFacts
    ) -> CostControlTotals:
        planned = self._sum_bucket_map(snapshot.planned_map, snapshot.project_currency)
        committed = self._sum_bucket_map(snapshot.committed_map, snapshot.project_currency)
        actual = self._sum_bucket_map(snapshot.actual_map, snapshot.project_currency)
        exposure = actual + committed
        forecast_etc = facts.control.forecast_etc
        estimate_at_completion = facts.control.estimate_at_completion
        variance_at_completion = facts.control.variance_at_completion
        return CostControlTotals(
            project_id=snapshot.project_id,
            project_currency=snapshot.project_currency,
            budget=snapshot.budget,
            planned=planned,
            committed=committed,
            actual=actual,
            forecast_etc=forecast_etc,
            estimate_at_completion=estimate_at_completion,
            variance_at_completion=variance_at_completion,
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
                    planned=Decimal("0"),
                    committed=Decimal("0"),
                    actual=Decimal("0"),
                    forecast=Decimal("0"),
                ),
            )
            if entry.stage in {"planned", "committed", "actual", "forecast"}:
                setattr(row, entry.stage, getattr(row, entry.stage) + entry.amount)
        rows = sorted(grouped.values(), key=lambda row: row.source_label.lower())
        return CostSourceBreakdown(
            project_id=facts.project_id,
            project_currency=project_currency,
            rows=rows,
            total_planned=sum((row.planned for row in rows), start=Decimal("0")),
            total_committed=sum((row.committed for row in rows), start=Decimal("0")),
            total_actual=sum((row.actual for row in rows), start=Decimal("0")),
            notes=[
                "Totals use versioned planned costs, Procurement commitments, and posted actual entries."
            ],
        )

    @staticmethod
    def _normalize_currency(value: str | None, fallback: str | None = None) -> str:
        return (value or fallback or "-").strip().upper() or "-"

    @staticmethod
    def _add_bucket(
        target: dict[CostBucketKey, Decimal],
        *,
        cost_type: CostType,
        currency: str,
        amount: Decimal | float,
    ) -> None:
        key = (cost_type, currency)
        target[key] = target.get(key, Decimal("0")) + Decimal(str(amount or 0))

    @staticmethod
    def _currency_in_scope(currency: str, project_currency: str | None) -> bool:
        return project_currency is None or currency.upper() == project_currency.upper()

    def _sum_bucket_map(
        self, values: dict[CostBucketKey, Decimal], project_currency: str | None
    ) -> Decimal:
        return sum(
            (
                amount
                for (_cost_type, currency), amount in values.items()
                if self._currency_in_scope(currency, project_currency)
            ),
            start=Decimal("0"),
        )

    def _sum_bucket_for_type(
        self,
        values: dict[CostBucketKey, Decimal],
        *,
        cost_type: CostType,
        project_currency: str | None,
    ) -> Decimal:
        return sum(
            (
                amount
                for (candidate, currency), amount in values.items()
                if candidate == cost_type
                and self._currency_in_scope(currency, project_currency)
            ),
            start=Decimal("0"),
        )

    def _sum_bucket_excluding_type(
        self,
        values: dict[CostBucketKey, Decimal],
        *,
        excluded_type: CostType,
        project_currency: str | None,
    ) -> Decimal:
        return sum(
            (
                amount
                for (candidate, currency), amount in values.items()
                if candidate != excluded_type
                and self._currency_in_scope(currency, project_currency)
            ),
            start=Decimal("0"),
        )

    @staticmethod
    def _sum_stage(entries: tuple[FinanceLedgerFact, ...], stage: str) -> Decimal:
        return sum(
            (entry.amount for entry in entries if entry.stage == stage),
            start=Decimal("0"),
        )


__all__ = [
    "CostControlTotals",
    "CostPolicyComposition",
    "CostPolicyEngine",
    "CostPolicySnapshot",
]
