from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

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
from src.core.modules.project_management.contracts.reads.portfolio.models.heatmap_facts import (
    HeatmapAssignmentFact,
    HeatmapDependencyFact,
    HeatmapProjectFacts,
    HeatmapResourceFact,
    HeatmapTaskFact,
    PortfolioHeatmapFacts,
)
from src.core.modules.project_management.infrastructure.persistence.orm.commitment import (
    ProjectCommitmentLineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.budget import (
    BudgetLineORM,
    ProjectBudgetORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_entry import (
    ProjectCostEntryORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.planned_cost import (
    ProjectPlannedCostLineORM,
    ProjectPlannedCostVersionORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectFinancialProfileORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskDependencyORM,
    TaskORM,
)


class SqlAlchemyPortfolioHeatmapReader:
    """Acquire all authorized heatmap facts with a fixed statement graph."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_ids: tuple[str, ...],
        as_of: date,
    ) -> PortfolioHeatmapFacts:
        project_ids = tuple(dict.fromkeys(project_ids))
        if not project_ids:
            return PortfolioHeatmapFacts(tenant_id, organization_id, as_of, (), ())
        project_scope = (
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
            ProjectORM.id.in_(project_ids),
        )
        approved_budget = (
            select(func.coalesce(func.sum(BudgetLineORM.amount), 0))
            .join(
                ProjectBudgetORM,
                (ProjectBudgetORM.id == BudgetLineORM.budget_id)
                & (ProjectBudgetORM.tenant_id == BudgetLineORM.tenant_id)
                & (ProjectBudgetORM.organization_id == BudgetLineORM.organization_id)
                & (ProjectBudgetORM.project_id == BudgetLineORM.project_id),
            )
            .where(
                ProjectBudgetORM.tenant_id == ProjectORM.tenant_id,
                ProjectBudgetORM.organization_id == ProjectORM.organization_id,
                ProjectBudgetORM.project_id == ProjectORM.id,
                ProjectBudgetORM.status == "approved",
            )
            .correlate(ProjectORM)
            .scalar_subquery()
        )
        project_rows = tuple(
            self._session.execute(
                select(
                    ProjectORM.id,
                    ProjectORM.name,
                    ProjectORM.status,
                    ProjectFinancialProfileORM.currency_code,
                    approved_budget.label("approved_budget"),
                    ProjectORM.start_date,
                    ProjectORM.end_date,
                )
                .join(
                    ProjectFinancialProfileORM,
                    (ProjectFinancialProfileORM.project_id == ProjectORM.id)
                    & (ProjectFinancialProfileORM.tenant_id == ProjectORM.tenant_id)
                    & (ProjectFinancialProfileORM.organization_id == ProjectORM.organization_id),
                )
                .where(*project_scope)
                .order_by(ProjectORM.id)
            )
        )
        scoped_project_ids = tuple(str(row.id) for row in project_rows)
        if not scoped_project_ids:
            return PortfolioHeatmapFacts(tenant_id, organization_id, as_of, (), ())

        task_rows = tuple(
            self._session.execute(
                select(
                    TaskORM.id,
                    TaskORM.project_id,
                    TaskORM.name,
                    TaskORM.parent_task_id,
                    TaskORM.wbs_code,
                    TaskORM.sort_order,
                    TaskORM.start_date,
                    TaskORM.end_date,
                    TaskORM.duration_days,
                    TaskORM.status,
                    TaskORM.priority,
                    TaskORM.percent_complete,
                    TaskORM.actual_start,
                    TaskORM.actual_end,
                    TaskORM.deadline,
                )
                .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
                .where(*project_scope)
                .order_by(TaskORM.project_id, TaskORM.id)
            )
        )
        predecessor = aliased(TaskORM)
        dependency_rows = tuple(
            self._session.execute(
                select(
                    TaskDependencyORM.id,
                    predecessor.project_id,
                    TaskDependencyORM.predecessor_task_id,
                    TaskDependencyORM.successor_task_id,
                    TaskDependencyORM.dependency_type,
                    TaskDependencyORM.lag_days,
                )
                .join(predecessor, predecessor.id == TaskDependencyORM.predecessor_task_id)
                .join(ProjectORM, ProjectORM.id == predecessor.project_id)
                .where(*project_scope)
                .order_by(predecessor.project_id, TaskDependencyORM.id)
            )
        )
        version_rows = tuple(
            self._session.execute(
                select(
                    ProjectPlannedCostVersionORM.id,
                    ProjectPlannedCostVersionORM.project_id,
                    ProjectPlannedCostVersionORM.as_of,
                    ProjectPlannedCostVersionORM.revision,
                )
                .where(
                    ProjectPlannedCostVersionORM.tenant_id == tenant_id,
                    ProjectPlannedCostVersionORM.organization_id == organization_id,
                    ProjectPlannedCostVersionORM.project_id.in_(scoped_project_ids),
                    ProjectPlannedCostVersionORM.as_of <= as_of,
                )
                .order_by(
                    ProjectPlannedCostVersionORM.project_id,
                    ProjectPlannedCostVersionORM.as_of.desc(),
                    ProjectPlannedCostVersionORM.revision.desc(),
                )
            )
        )
        latest_version_ids: dict[str, str] = {}
        version_as_of: dict[str, date] = {}
        for row in version_rows:
            project_id = str(row.project_id)
            if project_id not in latest_version_ids:
                latest_version_ids[project_id] = str(row.id)
                version_as_of[str(row.id)] = row.as_of
        planned_rows = tuple(
            self._session.execute(
                select(
                    ProjectPlannedCostLineORM.project_id,
                    ProjectPlannedCostLineORM.version_id,
                    ProjectPlannedCostLineORM.id,
                    ProjectPlannedCostLineORM.task_id,
                    ProjectPlannedCostLineORM.resource_id,
                    ProjectPlannedCostLineORM.source_assignment_id,
                    ProjectPlannedCostLineORM.currency_code,
                    ProjectPlannedCostLineORM.amount,
                )
                .where(ProjectPlannedCostLineORM.version_id.in_(tuple(latest_version_ids.values())))
                .order_by(ProjectPlannedCostLineORM.project_id, ProjectPlannedCostLineORM.id)
            )
        ) if latest_version_ids else ()
        commitment_rows = tuple(
            self._session.execute(
                select(ProjectCommitmentLineORM)
                .where(
                    ProjectCommitmentLineORM.tenant_id == tenant_id,
                    ProjectCommitmentLineORM.organization_id == organization_id,
                    ProjectCommitmentLineORM.project_id.in_(scoped_project_ids),
                    ProjectCommitmentLineORM.state != "cancelled",
                )
                .order_by(ProjectCommitmentLineORM.project_id, ProjectCommitmentLineORM.id)
            ).scalars()
        )
        actual_rows = tuple(
            self._session.execute(
                select(ProjectCostEntryORM)
                .where(
                    ProjectCostEntryORM.tenant_id == tenant_id,
                    ProjectCostEntryORM.organization_id == organization_id,
                    ProjectCostEntryORM.project_id.in_(scoped_project_ids),
                    ProjectCostEntryORM.status.in_(("posted", "reversed")),
                    ProjectCostEntryORM.posting_date <= as_of,
                )
                .order_by(ProjectCostEntryORM.project_id, ProjectCostEntryORM.posting_date, ProjectCostEntryORM.id)
            ).scalars()
        )
        project_resource_rows = tuple(
            self._session.execute(
                select(
                    ProjectResourceORM.project_id,
                    ProjectResourceORM.id,
                    ProjectResourceORM.resource_id,
                    ProjectResourceORM.planned_hours,
                    ProjectResourceORM.is_active,
                )
                .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
                .where(*project_scope)
                .order_by(ProjectResourceORM.project_id, ProjectResourceORM.id)
            )
        )
        assignment_rows = tuple(
            self._session.execute(
                select(
                    TaskORM.project_id,
                    TaskAssignmentORM.id,
                    TaskAssignmentORM.task_id,
                    TaskAssignmentORM.resource_id,
                    TaskAssignmentORM.allocation_percent,
                    TaskAssignmentORM.hours_logged,
                )
                .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
                .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
                .join(ResourceORM, ResourceORM.id == TaskAssignmentORM.resource_id)
                .where(
                    *project_scope,
                    ResourceORM.tenant_id == tenant_id,
                    ResourceORM.organization_id == organization_id,
                )
                .order_by(TaskORM.project_id, TaskAssignmentORM.id)
            )
        )
        resource_rows = tuple(
            self._session.execute(
                select(
                    ResourceORM.id,
                    ResourceORM.name,
                    ResourceORM.capacity_percent,
                    ResourceORM.is_active,
                )
                .where(
                    ResourceORM.tenant_id == tenant_id,
                    ResourceORM.organization_id == organization_id,
                )
                .order_by(ResourceORM.id)
            )
        )

        grouped: dict[str, dict[str, list[object]]] = defaultdict(lambda: defaultdict(list))
        for key, rows in (
            ("tasks", task_rows),
            ("dependencies", dependency_rows),
            ("project_resources", project_resource_rows),
            ("assignments", assignment_rows),
        ):
            for row in rows:
                grouped[str(row.project_id)][key].append(row)

        ledger_by_project: dict[str, list[FinanceLedgerFact]] = defaultdict(list)
        for row in planned_rows:
            ledger_by_project[str(row.project_id)].append(
                FinanceLedgerFact(
                    fact_id=str(row.id), task_id=str(row.task_id), resource_id=str(row.resource_id),
                    description=f"Assignment {row.source_assignment_id}", source_key="PLANNED_COST",
                    source_label="Planned Cost", reference_type="planned_cost_line", cost_type="LABOR",
                    stage="planned", currency_code=row.currency_code, amount=float(row.amount or 0),
                    occurred_on=version_as_of[str(row.version_id)],
                )
            )
        for row in commitment_rows:
            amount = row.matched_amount if row.state == "closed" else row.amount
            ledger_by_project[str(row.project_id)].append(
                FinanceLedgerFact(
                    fact_id=str(row.id), task_id=None if row.task_id is None else str(row.task_id),
                    resource_id=None, description=f"Purchase order line {row.purchase_order_line_id}",
                    source_key="PROCUREMENT_COMMITMENT", source_label="Procurement Commitment",
                    reference_type="commitment_line", cost_type="MATERIAL", stage="committed",
                    currency_code=row.currency_code, amount=float(amount or 0), occurred_on=row.order_date,
                )
            )
        for row in actual_rows:
            purpose = str(row.posting_purpose)
            source_key, source_label, cost_type = {
                "labor_actual": ("APPROVED_TIME", "Approved Time", "LABOR"),
                "receipt_accrual": ("PROCUREMENT_ACTUAL", "Procurement Actual", "MATERIAL"),
            }.get(purpose, ("MANUAL_ACTUAL", "Manual Actual", "OTHER"))
            ledger_by_project[str(row.project_id)].append(
                FinanceLedgerFact(
                    fact_id=str(row.id), task_id=None if row.task_id is None else str(row.task_id),
                    resource_id=None if row.resource_id is None else str(row.resource_id),
                    description=str(row.description), source_key=source_key, source_label=source_label,
                    reference_type="cost_entry", cost_type=cost_type, stage="actual",
                    currency_code=row.base_currency_code, amount=float(row.base_amount or 0),
                    occurred_on=row.posting_date,
                )
            )

        heatmap_resources = tuple(
            HeatmapResourceFact(
                id=str(row.id),
                name=str(row.name or ""),
                capacity_percent=float(row.capacity_percent or 100.0),
                is_active=bool(row.is_active),
            )
            for row in resource_rows
        )
        finance_resources = tuple(
            ResourceFact(
                resource_id=row.id,
                name=row.name,
                is_active=row.is_active,
            )
            for row in heatmap_resources
        )
        projects: list[HeatmapProjectFacts] = []
        for project_row in project_rows:
            project_id = str(project_row.id)
            rows = grouped[project_id]
            tasks = tuple(
                HeatmapTaskFact(
                    id=str(row.id),
                    project_id=project_id,
                    name=str(row.name or ""),
                    parent_task_id=(None if row.parent_task_id is None else str(row.parent_task_id)),
                    wbs_code=str(row.wbs_code or row.id),
                    sort_order=int(row.sort_order or 0),
                    start_date=row.start_date,
                    end_date=row.end_date,
                    duration_days=row.duration_days,
                    status=getattr(row.status, "value", str(row.status)),
                    priority=int(row.priority or 0),
                    percent_complete=float(row.percent_complete or 0.0),
                    actual_start=row.actual_start,
                    actual_end=row.actual_end,
                    deadline=row.deadline,
                )
                for row in rows["tasks"]
            )
            ledger_entries = tuple(ledger_by_project[project_id])
            aggregate_values: dict[tuple[str, str, str | None], tuple[float, int]] = {}
            for entry in ledger_entries:
                key = (entry.stage, entry.cost_type, entry.currency_code)
                amount, count = aggregate_values.get(key, (0.0, 0))
                aggregate_values[key] = (amount + entry.amount, count + 1)
            finance = FinanceSnapshotFacts(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=as_of,
                project=FinanceProjectFact(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    currency_code=str(project_row.currency_code),
                    approved_budget=float(project_row.approved_budget or 0.0),
                    start_date=project_row.start_date,
                    end_date=project_row.end_date,
                ),
                tasks=tuple(
                    TaskFact(
                        task_id=task.id,
                        name=task.name,
                        percent_complete=task.percent_complete,
                        start_date=task.start_date,
                        end_date=task.end_date,
                        actual_start=task.actual_start,
                        actual_end=task.actual_end,
                    )
                    for task in tasks
                ),
                ledger_entries=ledger_entries,
                cost_aggregates=tuple(
                    CostAggregateFact(
                        stage=stage,
                        cost_type=cost_type,
                        currency_code=currency,
                        total_amount=amount,
                        row_count=count,
                    )
                    for (stage, cost_type, currency), (amount, count) in aggregate_values.items()
                ),
                project_resources=tuple(
                    ProjectResourceFact(
                        project_resource_id=str(row.id),
                        resource_id=str(row.resource_id),
                        planned_hours=float(row.planned_hours or 0.0),
                        is_active=bool(row.is_active),
                    )
                    for row in rows["project_resources"]
                ),
                assignments=tuple(
                    LaborAssignmentFact(
                        assignment_id=str(row.id),
                        task_id=str(row.task_id),
                        resource_id=str(row.resource_id),
                        hours_logged=float(row.hours_logged or 0.0),
                    )
                    for row in rows["assignments"]
                ),
                resources=finance_resources,
            )
            projects.append(
                HeatmapProjectFacts(
                    project_id=project_id,
                    project_name=str(project_row.name or ""),
                    project_status=getattr(project_row.status, "value", str(project_row.status)),
                    finance=finance,
                    tasks=tasks,
                    dependencies=tuple(
                        HeatmapDependencyFact(
                            id=str(row.id),
                            project_id=project_id,
                            predecessor_task_id=str(row.predecessor_task_id),
                            successor_task_id=str(row.successor_task_id),
                            dependency_type=getattr(row.dependency_type, "value", str(row.dependency_type)),
                            lag_days=int(row.lag_days or 0),
                        )
                        for row in rows["dependencies"]
                    ),
                    assignments=tuple(
                        HeatmapAssignmentFact(
                            task_id=str(row.task_id),
                            resource_id=str(row.resource_id),
                            allocation_percent=float(row.allocation_percent or 0.0),
                        )
                        for row in rows["assignments"]
                    ),
                )
            )
        return PortfolioHeatmapFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            as_of=as_of,
            projects=tuple(projects),
            resources=heatmap_resources,
        )


__all__ = ["SqlAlchemyPortfolioHeatmapReader"]
