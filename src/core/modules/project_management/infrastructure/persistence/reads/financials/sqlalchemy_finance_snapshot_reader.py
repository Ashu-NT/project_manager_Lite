from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    CostAggregateFact,
    CostItemFact,
    FinanceProjectFact,
    FinanceSnapshotFacts,
    LaborAssignmentFact,
    ProjectResourceFact,
    ResourceFact,
    TaskFact,
)
from .statements.finance_snapshot_statements import (
    assignment_facts_statement,
    cost_aggregate_facts_statement,
    cost_item_facts_statement,
    project_fact_statement,
    project_resource_facts_statement,
    resource_facts_statement,
    task_facts_statement,
)


class SqlAlchemyFinanceSnapshotReader:
    """Acquire a complete, scoped fact set without returning ORM objects."""

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
        cost_items = tuple(
            CostItemFact(
                cost_item_id=str(row.id),
                task_id=(None if row.task_id is None else str(row.task_id)),
                description=str(row.description or ""),
                cost_type=str(row.cost_type or "OTHER"),
                currency_code=row.currency_code,
                planned_amount=float(row.planned_amount or 0.0),
                committed_amount=float(row.committed_amount or 0.0),
                actual_amount=float(row.actual_amount or 0.0),
                forecast_amount=(None if row.forecast_amount is None else float(row.forecast_amount)),
                commitment_status=str(row.commitment_status or ""),
                incurred_date=row.incurred_date,
            )
            for row in self._session.execute(
                cost_item_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                )
            )
        )
        aggregates = tuple(
            CostAggregateFact(
                cost_type=str(row[0] or "OTHER"),
                currency_code=row[1],
                commitment_status=str(row[2] or ""),
                positive_planned=float(row[3] or 0.0),
                positive_committed=float(row[4] or 0.0),
                positive_actual_as_of=float(row[5] or 0.0),
                raw_planned=float(row[6] or 0.0),
                raw_committed=float(row[7] or 0.0),
                raw_actual_as_of=float(row[8] or 0.0),
                row_count=int(row[9] or 0),
            )
            for row in self._session.execute(
                cost_aggregate_facts_statement(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    as_of=as_of,
                )
            )
        )
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
            cost_items=cost_items,
            cost_aggregates=aggregates,
            project_resources=project_resources,
            assignments=assignments,
            resources=resources,
        )


__all__ = ["SqlAlchemyFinanceSnapshotReader"]
