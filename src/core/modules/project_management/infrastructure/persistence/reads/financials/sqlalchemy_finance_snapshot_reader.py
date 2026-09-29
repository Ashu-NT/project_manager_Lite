from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_overview_facts import (
    FinanceOverviewFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    ActualMonthFact,
    ApprovedForecastFact,
    CostAggregateFact,
    FinanceControlFact,
    FinanceProjectFact,
    FinanceSnapshotFacts,
    LaborAssignmentFact,
    ProjectFinanceLedgerFact,
    ProjectResourceFact,
    ResourceFact,
    TaskFact,
)
from src.core.modules.project_management.contracts.reads.financials.models.project_finance_ledger_query import (
    ProjectFinanceLedgerQuery,
)
from src.core.platform.common.exceptions import BusinessRuleError

from .statements.finance_snapshot_statements import (
    actual_cost_total_statement,
    approved_forecast_facts_statement,
    approved_forecast_total_statement,
    assignment_facts_statement,
    commitment_total_statement,
    project_fact_statement,
    project_resource_facts_statement,
    resource_facts_statement,
    task_facts_statement,
)
from .statements.project_finance_ledger_statements import (
    ledger_aggregates_statement,
    ledger_page_statement,
    project_finance_ledger_relation,
    visible_ledger_relation,
)


class SqlAlchemyFinanceSnapshotReader:
    """Acquire scoped facts from canonical Project Finance authorities."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_overview_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        as_of: date,
    ) -> FinanceOverviewFacts | None:
        """Read bounded control totals without hydrating detailed finance rows."""
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
        actual_row = self._session.execute(
            actual_cost_total_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=as_of,
                project_currency=project_currency,
            )
        ).one()
        commitment_row = self._session.execute(
            commitment_total_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=as_of,
                project_currency=project_currency,
            )
        ).one()
        self._require_aggregate_currency(actual_row, source_label="Posted actual")
        self._require_aggregate_currency(commitment_row, source_label="Commitment")

        forecast_total = None
        if forecast_row is not None:
            forecast_total_row = self._session.execute(
                approved_forecast_total_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    forecast_id=str(forecast_row.id),
                    project_currency=project_currency,
                )
            ).one()
            self._require_aggregate_currency(
                forecast_total_row,
                source_label="Approved forecast",
            )
            forecast_total = Decimal(forecast_total_row.total_amount or 0)

        return FinanceOverviewFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            as_of=as_of,
            currency_code=project_currency,
            control=FinanceControlFact(
                approved_budget=Decimal(project_row.approved_budget or 0),
                posted_actual=Decimal(actual_row.total_amount or 0),
                open_commitment=Decimal(commitment_row.total_amount or 0),
                forecast_etc=forecast_total,
            ),
            approved_budget_id=(
                None
                if project_row.approved_budget_id is None
                else str(project_row.approved_budget_id)
            ),
            approved_budget_revision=(
                None
                if project_row.approved_budget_revision is None
                else int(project_row.approved_budget_revision)
            ),
            approved_budget_at=project_row.approved_budget_at,
            approved_forecast_id=(
                None if forecast_row is None else str(forecast_row.id)
            ),
            approved_forecast_revision=(
                None if forecast_row is None else int(forecast_row.revision)
            ),
            approved_forecast_as_of=(
                None if forecast_row is None else forecast_row.as_of_date
            ),
        )

    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        as_of: date,
        ledger_query: ProjectFinanceLedgerQuery | None = None,
        include_sensitive: bool = True,
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
                percent_complete=Decimal(str(row.percent_complete or 0)),
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
        ledger_query = ledger_query or ProjectFinanceLedgerQuery()
        ledger = project_finance_ledger_relation(
            tenant_id=tenant_id, organization_id=organization_id,
            project_id=project_id, as_of=as_of, project_currency=project_currency,
            forecast_id=None if forecast_row is None else str(forecast_row.id),
        )
        aggregate_rows = self._session.execute(ledger_aggregates_statement(ledger)).all()
        for row in aggregate_rows:
            self._require_aggregate_currency(row, source_label="Ledger")
        aggregates = tuple(
            CostAggregateFact(
                stage=row.stage, cost_type=row.cost_type, currency_code=row.currency_code,
                total_amount=Decimal(row.total_amount), row_count=row.row_count,
                source_key=row.source_key, source_label=row.source_label,
            ) for row in aggregate_rows
        )
        visible = visible_ledger_relation(ledger, include_sensitive=include_sensitive, as_of=as_of)
        ledger_total = self._session.scalar(select(func.count()).select_from(visible))
        ledger_entries = tuple(
            ProjectFinanceLedgerFact(**{
                key: value for key, value in row._mapping.items()
                if key != "currency_mismatch_count"
            })
            for row in self._session.execute(ledger_page_statement(visible, ledger_query))
        )
        year = func.extract("year", ledger.c.occurred_on)
        month = func.extract("month", ledger.c.occurred_on)
        actual_months = tuple(
            ActualMonthFact(year=int(row.year), month=int(row.month), amount=Decimal(row.amount))
            for row in self._session.execute(
                select(year.label("year"), month.label("month"), func.sum(ledger.c.amount).label("amount"))
                .where(ledger.c.stage == "actual")
                .group_by(year, month).order_by(year, month)
            )
        )
        def stage_total(stage):
            return sum((row.total_amount for row in aggregates if row.stage == stage), Decimal(0))
        forecast_etc = stage_total("forecast")
        approved_forecast = None
        if forecast_row is not None:
            approved_forecast = ApprovedForecastFact(
                forecast_id=str(forecast_row.id),
                revision=int(forecast_row.revision),
                name=str(forecast_row.name),
                currency_code=str(forecast_row.currency_code),
                as_of_date=forecast_row.as_of_date,
                etc_total=forecast_etc,
                line_count=sum(row.row_count for row in aggregates if row.stage == "forecast"),
            )

        project_resources = tuple(
            ProjectResourceFact(
                project_resource_id=str(row.id),
                resource_id=str(row.resource_id),
                planned_hours=row.planned_hours or Decimal(0),
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
                hours_logged=row.hours_logged or Decimal(0),
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
                posted_actual=stage_total("actual"),
                open_commitment=stage_total("committed"),
                forecast_etc=(None if approved_forecast is None else forecast_etc),
            ),
            tasks=tasks,
            ledger_entries=ledger_entries,
            ledger_total=int(ledger_total),
            ledger_offset=ledger_query.offset,
            ledger_limit=ledger_query.limit,
            actual_months=actual_months,
            cost_aggregates=aggregates,
            project_resources=project_resources,
            assignments=assignments,
            resources=resources,
        )

    @staticmethod
    def _require_aggregate_currency(row, *, source_label: str) -> None:
        if int(row.currency_mismatch_count or 0) > 0:
            raise BusinessRuleError(
                f"{source_label} currency cannot be reconciled to project currency.",
                code="PROJECT_FINANCE_READ_CURRENCY_MISMATCH",
            )


__all__ = ["SqlAlchemyFinanceSnapshotReader"]
