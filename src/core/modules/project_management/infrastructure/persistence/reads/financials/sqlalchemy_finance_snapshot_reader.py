from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    ApprovedForecastFact,
    CostAggregateFact,
    FinanceControlFact,
    FinanceLedgerFact,
    FinanceProjectFact,
    FinanceSnapshotFacts,
    LaborAssignmentFact,
    ProjectResourceFact,
    ResourceFact,
    TaskFact,
)
from src.core.platform.common.exceptions import BusinessRuleError
from .statements.finance_snapshot_statements import (
    actual_cost_facts_statement,
    approved_forecast_facts_statement,
    approved_forecast_line_facts_statement,
    assignment_facts_statement,
    commitment_facts_statement,
    planned_cost_facts_statement,
    project_fact_statement,
    project_resource_facts_statement,
    resource_facts_statement,
    task_facts_statement,
)


class SqlAlchemyFinanceSnapshotReader:
    """Acquire scoped facts from canonical Project Finance authorities."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        as_of: date,
    ) -> FinanceSnapshotFacts | None:
        project_row = self._session.execute(
            project_fact_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            )
        ).one_or_none()
        if project_row is None:
            return None
        project_currency = str(project_row.currency_code).strip().upper()
        forecast_row = self._session.execute(
            approved_forecast_facts_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=as_of,
            )
        ).one_or_none()

        tasks = tuple(
            TaskFact(
                task_id=str(row.id),
                name=str(row.name),
                percent_complete=float(row.percent_complete or 0.0),
                start_date=row.start_date,
                end_date=row.end_date,
                actual_start=row.actual_start,
                actual_end=row.actual_end,
            )
            for row in self._session.execute(
                task_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                )
            )
        )
        ledger_entries = self._read_ledger_entries(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            as_of=as_of,
            project_currency=project_currency,
            forecast_id=(None if forecast_row is None else str(forecast_row.id)),
        )
        aggregates = self._aggregate(ledger_entries)
        forecast_etc = self._stage_total(ledger_entries, "forecast")
        approved_forecast = None
        if forecast_row is not None:
            approved_forecast = ApprovedForecastFact(
                forecast_id=str(forecast_row.id),
                revision=int(forecast_row.revision),
                name=str(forecast_row.name),
                currency_code=str(forecast_row.currency_code),
                as_of_date=forecast_row.as_of_date,
                etc_total=forecast_etc,
                line_count=sum(1 for row in ledger_entries if row.stage == "forecast"),
            )

        project_resources = tuple(
            ProjectResourceFact(
                project_resource_id=str(row.id),
                resource_id=str(row.resource_id),
                planned_hours=row.planned_hours or Decimal("0"),
                is_active=bool(row.is_active),
            )
            for row in self._session.execute(
                project_resource_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                )
            )
        )
        assignments = tuple(
            LaborAssignmentFact(
                assignment_id=str(row.id),
                task_id=str(row.task_id),
                resource_id=str(row.resource_id),
                hours_logged=row.hours_logged or Decimal("0"),
            )
            for row in self._session.execute(
                assignment_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                )
            )
        )
        resource_ids = tuple(
            sorted(
                {row.resource_id for row in project_resources}
                | {row.resource_id for row in assignments}
                | {
                    row.resource_id
                    for row in ledger_entries
                    if row.resource_id is not None
                }
            )
        )
        resources = (
            tuple(
                ResourceFact(
                    resource_id=str(row.id),
                    name=str(row.name or ""),
                    is_active=bool(row.is_active),
                )
                for row in self._session.execute(
                    resource_facts_statement(
                        tenant_id=tenant_id,
                        organization_id=organization_id,
                        project_id=project_id,
                        resource_ids=resource_ids,
                    )
                )
            )
            if resource_ids
            else ()
        )
        project = FinanceProjectFact(
            project_id=str(project_row.id),
            tenant_id=str(project_row.tenant_id),
            organization_id=str(project_row.organization_id),
            currency_code=str(project_row.currency_code),
            approved_budget=Decimal(project_row.approved_budget or 0),
            approved_budget_id=(
                None if project_row.approved_budget_id is None
                else str(project_row.approved_budget_id)
            ),
            approved_budget_revision=(
                None if project_row.approved_budget_revision is None
                else int(project_row.approved_budget_revision)
            ),
            start_date=project_row.start_date,
            end_date=project_row.end_date,
        )
        return FinanceSnapshotFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            as_of=as_of,
            project=project,
            approved_forecast=approved_forecast,
            control=FinanceControlFact(
                approved_budget=project.approved_budget,
                posted_actual=self._stage_total(ledger_entries, "actual"),
                open_commitment=self._stage_total(ledger_entries, "committed"),
                forecast_etc=(None if approved_forecast is None else forecast_etc),
            ),
            tasks=tasks,
            ledger_entries=ledger_entries,
            cost_aggregates=aggregates,
            project_resources=project_resources,
            assignments=assignments,
            resources=resources,
        )

    def _read_ledger_entries(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        as_of: date,
        project_currency: str,
        forecast_id: str | None,
    ) -> tuple[FinanceLedgerFact, ...]:
        planned = tuple(
            FinanceLedgerFact(
                fact_id=str(row.id),
                task_id=str(row.task_id),
                resource_id=str(row.resource_id),
                description=f"Assignment {row.source_assignment_id}",
                source_key="PLANNED_COST",
                source_label="Planned Cost",
                reference_type="planned_cost_line",
                cost_type="LABOR",
                stage="planned",
                currency_code=project_currency,
                amount=self._require_project_currency_amount(
                    amount=row.amount,
                    currency_code=row.currency_code,
                    project_currency=project_currency,
                    source_label="Planned cost",
                ),
                occurred_on=row.as_of,
                cost_code_id=str(row.cost_code_id),
                source_type="planned_cost",
            )
            for row in self._session.execute(
                planned_cost_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    as_of=as_of,
                )
            )
        )
        forecasts = tuple(
            FinanceLedgerFact(
                fact_id=str(row.id),
                task_id=None if row.task_id is None else str(row.task_id),
                resource_id=None,
                description=str(row.description),
                source_key="APPROVED_FORECAST",
                source_label="Approved Forecast ETC",
                reference_type="forecast_line",
                cost_type="OTHER",
                stage="forecast",
                currency_code=project_currency,
                amount=self._require_project_currency_amount(
                    amount=row.amount,
                    currency_code=row.currency_code,
                    project_currency=project_currency,
                    source_label="Approved forecast",
                ),
                occurred_on=row.period_start or row.as_of_date,
                cost_code_id=str(row.cost_code_id),
                source_type=str(row.source_type),
                period_start=row.period_start,
                period_end=row.period_end,
            )
            for row in (
                self._session.execute(
                    approved_forecast_line_facts_statement(
                        tenant_id=tenant_id,
                        organization_id=organization_id,
                        project_id=project_id,
                        forecast_id=forecast_id,
                    )
                )
                if forecast_id is not None
                else ()
            )
        )
        commitments = tuple(
            FinanceLedgerFact(
                fact_id=str(row.id),
                task_id=None if row.task_id is None else str(row.task_id),
                resource_id=None,
                description=f"Purchase order line {row.purchase_order_line_id}",
                source_key="PROCUREMENT_COMMITMENT",
                source_label="Procurement Commitment",
                reference_type="commitment_line",
                cost_type="MATERIAL",
                stage="committed",
                currency_code=project_currency,
                amount=self._commitment_amount(row, project_currency),
                occurred_on=row.order_date,
                cost_code_id=str(row.cost_code_id),
                source_type="open_commitment",
            )
            for row in self._session.execute(
                commitment_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    as_of=as_of,
                )
            )
        )
        actuals = tuple(
            FinanceLedgerFact(
                fact_id=str(row.id),
                task_id=None if row.task_id is None else str(row.task_id),
                resource_id=None if row.resource_id is None else str(row.resource_id),
                description=str(row.description),
                source_key=str(row.source_key),
                source_label={
                    "APPROVED_TIME": "Approved Time",
                    "PROCUREMENT_ACTUAL": "Procurement Actual",
                    "MANUAL_ACTUAL": "Manual Actual",
                }[str(row.source_key)],
                reference_type="cost_entry",
                cost_type=str(row.cost_type),
                stage="actual",
                currency_code=project_currency,
                amount=self._actual_amount(row, project_currency),
                occurred_on=row.posting_date,
                cost_code_id=str(row.cost_code_id),
                source_type=str(row.source_key).lower(),
                financial_period_id=(
                    None
                    if row.financial_period_id is None
                    else str(row.financial_period_id)
                ),
            )
            for row in self._session.execute(
                actual_cost_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    as_of=as_of,
                )
            )
        )
        return planned + forecasts + commitments + actuals

    @staticmethod
    def _aggregate(
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
            for (stage, cost_type, currency), (amount, count) in sorted(
                buckets.items(), key=lambda item: tuple(value or "" for value in item[0])
            )
        )

    @staticmethod
    def _stage_total(entries: tuple[FinanceLedgerFact, ...], stage: str) -> Decimal:
        return sum(
            (entry.amount for entry in entries if entry.stage == stage),
            start=Decimal("0"),
        )

    @staticmethod
    def _require_project_currency_amount(
        *, amount, currency_code: str | None, project_currency: str, source_label: str
    ) -> Decimal:
        if str(currency_code or "").strip().upper() != project_currency:
            raise BusinessRuleError(
                f"{source_label} currency cannot be reconciled to project currency.",
                code="PROJECT_FINANCE_READ_CURRENCY_MISMATCH",
            )
        return Decimal(amount or 0)

    @staticmethod
    def _actual_amount(row, project_currency: str) -> Decimal:
        if str(row.currency_code).upper() == project_currency:
            return Decimal(row.amount or 0)
        if str(row.base_currency_code or "").upper() == project_currency and row.base_amount is not None:
            return Decimal(row.base_amount)
        raise BusinessRuleError(
            "Posted actual currency cannot be reconciled to project currency.",
            code="PROJECT_FINANCE_READ_CURRENCY_MISMATCH",
        )

    @staticmethod
    def _commitment_amount(row, project_currency: str) -> Decimal:
        if str(row.state) in {"closed", "cancelled"}:
            return Decimal("0")
        matched = Decimal(row.matched_amount or 0)
        if str(row.currency_code).upper() == project_currency:
            return max(Decimal("0"), Decimal(row.amount or 0) - matched)
        if str(row.base_currency_code).upper() == project_currency:
            matched_base = matched * Decimal(row.exchange_rate or 0)
            return max(Decimal("0"), Decimal(row.base_amount or 0) - matched_base)
        raise BusinessRuleError(
            "Commitment currency cannot be reconciled to project currency.",
            code="PROJECT_FINANCE_READ_CURRENCY_MISMATCH",
        )


__all__ = ["SqlAlchemyFinanceSnapshotReader"]
