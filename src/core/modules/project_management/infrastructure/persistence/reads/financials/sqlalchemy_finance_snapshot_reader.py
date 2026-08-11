from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    CostAggregateFact,
    FinanceLedgerFact,
    FinanceProjectFact,
    FinanceSnapshotFacts,
    LaborAssignmentFact,
    ProjectResourceFact,
    ResourceFact,
    TaskFact,
)
from .statements.finance_snapshot_statements import (
    actual_cost_facts_statement,
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
        )
        aggregates = self._aggregate(ledger_entries)

        project_resources = tuple(
            ProjectResourceFact(
                project_resource_id=str(row.id),
                resource_id=str(row.resource_id),
                planned_hours=float(row.planned_hours or 0.0),
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
                hours_logged=float(row.hours_logged or 0.0),
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
            currency=project_row.currency,
            planned_budget=float(project_row.planned_budget or 0.0),
            start_date=project_row.start_date,
            end_date=project_row.end_date,
        )
        return FinanceSnapshotFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            as_of=as_of,
            project=project,
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
                currency_code=row.currency_code,
                amount=float(row.amount or 0),
                occurred_on=row.as_of,
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
                currency_code=row.currency_code,
                amount=float(row.effective_amount or 0),
                occurred_on=row.order_date,
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
                currency_code=row.base_currency_code,
                amount=float(row.base_amount or 0),
                occurred_on=row.posting_date,
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
        return planned + commitments + actuals

    @staticmethod
    def _aggregate(
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
            for (stage, cost_type, currency), (amount, count) in sorted(
                buckets.items(), key=lambda item: tuple(value or "" for value in item[0])
            )
        )


__all__ = ["SqlAlchemyFinanceSnapshotReader"]
