from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingFacts,
    CostPhasingPeriodFact,
    CostPhasingQuery,
    CostPhasingSeriesAvailabilityFact,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.statements.finance_snapshot_statements import (
    actual_cost_facts_statement,
    approved_forecast_facts_statement,
    approved_forecast_line_facts_statement,
    commitment_facts_statement,
    evm_baseline_statement,
    evm_baseline_task_facts_statement,
    project_fact_statement,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.modules.project_management.domain.financials.commitment import (
    open_commitment_amount,
)


class SqlAlchemyFinancePerformanceReader:
    """Read only the scoped cost-stage facts required by Performance."""

    def __init__(
        self,
        *,
        session: Session,
        calendar: CalendarProtocol | None = None,
    ) -> None:
        self._session = session
        self._calendar = calendar

    def read_cost_phasing(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        query: CostPhasingQuery,
    ) -> CostPhasingFacts | None:
        project = self._session.execute(
            project_fact_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            )
        ).one_or_none()
        if project is None:
            return None

        currency = str(project.currency_code or "").strip().upper()
        forecast = self._session.execute(
            approved_forecast_facts_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=query.date_to,
            )
        ).one_or_none()
        buckets: dict[str, dict[str, object]] = {}
        availability: dict[str, CostPhasingSeriesAvailabilityFact] = {}

        def add(stage: str, anchor: date | None, amount: Decimal) -> None:
            resolved_anchor = anchor or query.date_to
            if resolved_anchor < query.date_from or resolved_anchor > query.date_to:
                return
            key, starts_on, ends_on = self._period_bounds(
                resolved_anchor,
                query.granularity,
            )
            bucket = buckets.setdefault(
                key,
                {
                    "period_start": starts_on,
                    "period_end": ends_on,
                    "planned": Decimal("0"),
                    "committed": Decimal("0"),
                    "actual": Decimal("0"),
                    "forecast": Decimal("0"),
                },
            )
            bucket[stage] = Decimal(bucket[stage]) + amount

        baseline_id = self._session.execute(
            evm_baseline_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                baseline_id=None,
            )
        ).scalar_one_or_none()
        if baseline_id is None:
            availability["planned"] = CostPhasingSeriesAvailabilityFact(
                series_code="planned",
                availability="baseline_unavailable",
                unavailable_reason="No approved cost-loaded baseline is available for Cost Phasing.",
            )
        elif self._calendar is None:
            availability["planned"] = CostPhasingSeriesAvailabilityFact(
                series_code="planned",
                availability="calendar_unavailable",
                unavailable_reason="The enterprise calendar is unavailable for baseline cost distribution.",
            )
        else:
            baseline_rows = tuple(self._session.execute(
                evm_baseline_task_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    baseline_id=str(baseline_id),
                )
            ))
            planned_available = self._add_baseline_phasing(
                buckets=buckets,
                rows=baseline_rows,
                query=query,
                add=add,
            )
            availability["planned"] = CostPhasingSeriesAvailabilityFact(
                series_code="planned",
                availability="available" if planned_available else "calendar_unavailable",
                unavailable_reason=(
                    "The enterprise calendar cannot expose working-day dates for baseline cost distribution."
                    if not planned_available
                    else ""
                ),
            )

        if forecast is not None:
            unphased_forecast = False
            for row in self._session.execute(
                approved_forecast_line_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    forecast_id=str(forecast.id),
                    date_from=query.date_from,
                    date_to=query.date_to,
                )
            ):
                if row.period_start is None or row.period_end is None:
                    unphased_forecast = True
                    continue
                if self._period_bounds(row.period_start, query.granularity)[0] != self._period_bounds(row.period_end, query.granularity)[0]:
                    unphased_forecast = True
                    continue
                add("forecast", row.period_start, self._project_currency_amount(row.amount, row.currency_code, currency, "Approved forecast"))
            availability["forecast"] = CostPhasingSeriesAvailabilityFact(
                series_code="forecast",
                availability="partially_unphased" if unphased_forecast else "available",
                unavailable_reason=("Some approved Forecast lines span multiple periods or have no period evidence; they are not fabricated into monthly values." if unphased_forecast else ""),
            )
        else:
            availability["forecast"] = CostPhasingSeriesAvailabilityFact(
                series_code="forecast", availability="forecast_unavailable", unavailable_reason="No approved Forecast exists for this as-of date."
            )

        unphased_commitment = False
        for row in self._session.execute(
            commitment_facts_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=query.date_to,
                date_from=query.date_from,
            )
        ):
            if row.expected_delivery_date is None:
                unphased_commitment = True
                continue
            add("committed", row.expected_delivery_date, self._commitment_amount(row, currency))
        availability["commitment"] = CostPhasingSeriesAvailabilityFact(
            series_code="commitment",
            availability="partially_unphased" if unphased_commitment else "available",
            unavailable_reason=("Some open Commitments have no expected delivery date and are excluded from period allocation." if unphased_commitment else ""),
        )

        for row in self._session.execute(
            actual_cost_facts_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=query.date_to,
                date_from=query.date_from,
            )
        ):
            add("actual", row.posting_date, self._actual_amount(row, currency))
        availability["actual"] = CostPhasingSeriesAvailabilityFact(
            series_code="actual", availability="available"
        )

        periods = tuple(
            CostPhasingPeriodFact(
                period_key=key,
                period_start=value["period_start"],  # type: ignore[arg-type]
                period_end=value["period_end"],  # type: ignore[arg-type]
                planned_cost=Decimal(value["planned"]),
                open_commitment=Decimal(value["committed"]),
                posted_actual=Decimal(value["actual"]),
                forecast_cost=Decimal(value["forecast"]),
                exposure=Decimal(value["actual"]) + Decimal(value["forecast"]),
                currency_code=currency,
            )
            for key, value in sorted(
                buckets.items(), key=lambda item: item[1]["period_start"]
            )
        )
        return CostPhasingFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            as_of_date=query.date_to,
            date_from=query.date_from,
            date_to=query.date_to,
            granularity=query.granularity,
            currency_code=currency,
            approved_budget_id=(
                None if project.approved_budget_id is None else str(project.approved_budget_id)
            ),
            approved_budget_revision=(
                None
                if project.approved_budget_revision is None
                else int(project.approved_budget_revision)
            ),
            approved_forecast_id=(None if forecast is None else str(forecast.id)),
            approved_forecast_revision=(
                None if forecast is None else int(forecast.revision)
            ),
            approved_forecast_as_of=(
                None if forecast is None else forecast.as_of_date
            ),
            series_availability=tuple(availability[key] for key in ("planned", "actual", "forecast", "commitment")),
            periods=periods,
        )

    def _add_baseline_phasing(self, *, buckets, rows, query, add) -> bool:
        """Allocate approved baseline task cost evenly across enterprise working days."""
        loader = getattr(self._calendar, "working_day_dates_between", None)
        if callable(loader):
            starts = [row.baseline_start for row in rows if row.baseline_start is not None]
            ends = [row.baseline_finish for row in rows if row.baseline_finish is not None]
            if not starts or not ends:
                return True
            working_dates = tuple(loader(min(starts), max(ends)))
        else:
            # The legacy calendar contract can count days but cannot expose
            # their identities, so it cannot truthfully allocate monthly cost.
            return False
        for row in rows:
            if row.baseline_start is None or row.baseline_finish is None:
                continue
            days = tuple(day for day in working_dates if row.baseline_start <= day <= row.baseline_finish)
            if not days:
                continue
            daily = Decimal(row.baseline_planned_cost or 0) / Decimal(len(days))
            allocated = Decimal("0")
            for index, day in enumerate(days):
                amount = Decimal(row.baseline_planned_cost or 0) - allocated if index == len(days) - 1 else daily
                allocated += amount
                if query.date_from <= day <= query.date_to:
                    add("planned", day, amount)
        return True

    @staticmethod
    def _period_bounds(anchor: date, granularity: str) -> tuple[str, date, date]:
        if granularity == "quarter":
            quarter = ((anchor.month - 1) // 3) + 1
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            return (
                f"{anchor.year}-Q{quarter}",
                date(anchor.year, start_month, 1),
                date(
                    anchor.year,
                    end_month,
                    monthrange(anchor.year, end_month)[1],
                ),
            )
        return (
            f"{anchor.year}-{anchor.month:02d}",
            date(anchor.year, anchor.month, 1),
            date(
                anchor.year,
                anchor.month,
                monthrange(anchor.year, anchor.month)[1],
            ),
        )

    @staticmethod
    def _project_currency_amount(
        amount: object,
        currency_code: str | None,
        project_currency: str,
        source_label: str,
    ) -> Decimal:
        if str(currency_code or "").strip().upper() != project_currency:
            raise BusinessRuleError(
                f"{source_label} currency cannot be reconciled to project currency.",
                code="PROJECT_FINANCE_READ_CURRENCY_MISMATCH",
            )
        return Decimal(amount or 0)

    @staticmethod
    def _actual_amount(row: object, project_currency: str) -> Decimal:
        if str(row.currency_code or "").strip().upper() == project_currency:
            return Decimal(row.amount or 0)
        if (
            str(row.base_currency_code or "").strip().upper() == project_currency
            and row.base_amount is not None
        ):
            return Decimal(row.base_amount)
        raise BusinessRuleError(
            "Posted actual currency cannot be reconciled to project currency.",
            code="PROJECT_FINANCE_READ_CURRENCY_MISMATCH",
        )

    @staticmethod
    def _commitment_amount(row: object, project_currency: str) -> Decimal:
        return open_commitment_amount(
            state=row.state,
            amount=row.amount,
            matched_amount=row.matched_amount,
            currency_code=row.currency_code,
            base_amount=row.base_amount,
            base_currency_code=row.base_currency_code,
            exchange_rate=row.exchange_rate,
            target_currency=project_currency,
            currency_mismatch_code="PROJECT_FINANCE_READ_CURRENCY_MISMATCH",
        )


__all__ = ["SqlAlchemyFinancePerformanceReader"]
