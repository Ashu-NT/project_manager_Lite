from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

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
from src.core.modules.project_management.contracts.reads.portfolio.models.heatmap_facts import (
    HeatmapAssignmentFact,
    HeatmapDependencyFact,
    HeatmapProjectFacts,
    HeatmapResourceFact,
    HeatmapTaskFact,
    PortfolioHeatmapFacts,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost import CostItemORM
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
        project_rows = tuple(
            self._session.execute(
                select(
                    ProjectORM.id,
                    ProjectORM.name,
                    ProjectORM.status,
                    ProjectORM.currency,
                    ProjectORM.planned_budget,
                    ProjectORM.start_date,
                    ProjectORM.end_date,
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
        cost_rows = tuple(
            self._session.execute(
                select(
                    CostItemORM.project_id,
                    CostItemORM.id,
                    CostItemORM.task_id,
                    CostItemORM.description,
                    CostItemORM.cost_type,
                    CostItemORM.currency_code,
                    CostItemORM.planned_amount,
                    CostItemORM.committed_amount,
                    CostItemORM.actual_amount,
                    CostItemORM.forecast_amount,
                    CostItemORM.commitment_status,
                    CostItemORM.incurred_date,
                )
                .join(ProjectORM, ProjectORM.id == CostItemORM.project_id)
                .where(*project_scope)
                .order_by(CostItemORM.project_id, CostItemORM.id)
            )
        )
        actual_in_scope = or_(CostItemORM.incurred_date.is_(None), CostItemORM.incurred_date <= as_of)
        aggregate_dimensions = (
            CostItemORM.project_id,
            CostItemORM.cost_type,
            CostItemORM.currency_code,
            CostItemORM.commitment_status,
        )
        aggregate_rows = tuple(
            self._session.execute(
                select(
                    *aggregate_dimensions,
                    func.sum(case((CostItemORM.planned_amount > 0, CostItemORM.planned_amount), else_=0.0)),
                    func.sum(case((CostItemORM.committed_amount > 0, CostItemORM.committed_amount), else_=0.0)),
                    func.sum(
                        case(
                            (and_(actual_in_scope, CostItemORM.actual_amount > 0), CostItemORM.actual_amount),
                            else_=0.0,
                        )
                    ),
                    func.sum(CostItemORM.planned_amount),
                    func.sum(CostItemORM.committed_amount),
                    func.sum(case((actual_in_scope, CostItemORM.actual_amount), else_=0.0)),
                    func.count(CostItemORM.id),
                )
                .join(ProjectORM, ProjectORM.id == CostItemORM.project_id)
                .where(*project_scope)
                .group_by(*aggregate_dimensions)
                .order_by(*aggregate_dimensions)
            )
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
            ("costs", cost_rows),
            ("aggregates", aggregate_rows),
            ("project_resources", project_resource_rows),
            ("assignments", assignment_rows),
        ):
            for row in rows:
                grouped[str(row.project_id)][key].append(row)

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
            costs = tuple(
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
                for row in rows["costs"]
            )
            finance = FinanceSnapshotFacts(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                as_of=as_of,
                project=FinanceProjectFact(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    currency=project_row.currency,
                    planned_budget=float(project_row.planned_budget or 0.0),
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
                cost_items=costs,
                cost_aggregates=tuple(
                    CostAggregateFact(
                        cost_type=str(row.cost_type or "OTHER"),
                        currency_code=row.currency_code,
                        commitment_status=str(row.commitment_status or ""),
                        positive_planned=float(row[4] or 0.0),
                        positive_committed=float(row[5] or 0.0),
                        positive_actual_as_of=float(row[6] or 0.0),
                        raw_planned=float(row[7] or 0.0),
                        raw_committed=float(row[8] or 0.0),
                        raw_actual_as_of=float(row[9] or 0.0),
                        row_count=int(row[10] or 0),
                    )
                    for row in rows["aggregates"]
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
