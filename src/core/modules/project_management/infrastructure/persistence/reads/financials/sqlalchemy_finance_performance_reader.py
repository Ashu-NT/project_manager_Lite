from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingFacts,
    CostPhasingPeriodFact,
    CostPhasingQuery,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.statements.finance_snapshot_statements import (
    actual_cost_facts_statement,
    approved_forecast_facts_statement,
    approved_forecast_line_facts_statement,
    commitment_facts_statement,
    planned_cost_facts_statement,
    project_fact_statement,
)
from src.core.platform.common.exceptions import BusinessRuleError


class SqlAlchemyFinancePerformanceReader:
    """Read only the scoped cost-stage facts required by Performance."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

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

        for row in self._session.execute(
            planned_cost_facts_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=query.date_to,
                date_from=query.date_from,
            )
        ):
            add(
                "planned",
                row.as_of,
                self._project_currency_amount(
                    row.amount,
                    row.currency_code,
                    currency,
                    "Planned cost",
                ),
            )

        if forecast is not None:
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
                add(
                    "forecast",
                    row.period_start or row.as_of_date,
                    self._project_currency_amount(
                        row.amount,
                        row.currency_code,
                        currency,
                        "Approved forecast",
                    ),
                )

        for row in self._session.execute(
            commitment_facts_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=query.date_to,
                date_from=query.date_from,
            )
        ):
            add("committed", row.order_date, self._commitment_amount(row, currency))

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
            periods=periods,
        )

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
        if str(row.state) in {"closed", "cancelled"}:
            return Decimal("0")
        matched = Decimal(row.matched_amount or 0)
        if str(row.currency_code or "").strip().upper() == project_currency:
            return max(Decimal("0"), Decimal(row.amount or 0) - matched)
        if str(row.base_currency_code or "").strip().upper() == project_currency:
            matched_base = matched * Decimal(row.exchange_rate or 0)
            return max(Decimal("0"), Decimal(row.base_amount or 0) - matched_base)
        raise BusinessRuleError(
            "Commitment currency cannot be reconciled to project currency.",
            code="PROJECT_FINANCE_READ_CURRENCY_MISMATCH",
        )


__all__ = ["SqlAlchemyFinancePerformanceReader"]
