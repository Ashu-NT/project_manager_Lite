from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.portfolio.models.resource_pool_facts import (
    PortfolioDemandFact,
    PortfolioResourceFact,
    PortfolioResourcePoolFacts,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)


class SqlAlchemyPortfolioResourcePoolReader:
    """Read a scoped portfolio capacity fact set without hydrating ORM entities."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        from_date: date,
        to_date: date,
        resource_ids: tuple[str, ...] | None = None,
    ) -> PortfolioResourcePoolFacts:
        resource_stmt = select(
            ResourceORM.id,
            ResourceORM.name,
            ResourceORM.capacity_percent,
        ).where(
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
        )
        if resource_ids is None:
            resource_stmt = resource_stmt.where(ResourceORM.is_active.is_(True))
        elif not resource_ids:
            return PortfolioResourcePoolFacts(tenant_id, organization_id, (), ())
        else:
            resource_stmt = resource_stmt.where(ResourceORM.id.in_(resource_ids))
        resource_stmt = resource_stmt.order_by(ResourceORM.name, ResourceORM.id)

        resources = tuple(
            PortfolioResourceFact(
                resource_id=str(row.id),
                name=str(row.name or ""),
                capacity_percent=float(row.capacity_percent or 100.0),
            )
            for row in self._session.execute(resource_stmt)
        )
        scoped_resource_ids = tuple(row.resource_id for row in resources)
        if not scoped_resource_ids:
            return PortfolioResourcePoolFacts(tenant_id, organization_id, resources, ())

        task_start = func.coalesce(TaskORM.start_date, TaskORM.actual_start)
        task_end = func.coalesce(TaskORM.end_date, TaskORM.actual_end)
        demand_stmt = (
            select(
                TaskAssignmentORM.resource_id,
                TaskAssignmentORM.task_id,
                ProjectORM.id.label("project_id"),
                ProjectORM.name.label("project_name"),
                task_start.label("start_date"),
                task_end.label("end_date"),
                TaskAssignmentORM.allocation_percent,
            )
            .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .join(ResourceORM, ResourceORM.id == TaskAssignmentORM.resource_id)
            .where(
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
                ResourceORM.tenant_id == tenant_id,
                ResourceORM.organization_id == organization_id,
                TaskAssignmentORM.resource_id.in_(scoped_resource_ids),
                task_start.is_not(None),
                task_end.is_not(None),
                task_end >= from_date,
                task_start <= to_date,
            )
            .order_by(TaskAssignmentORM.resource_id, ProjectORM.name, TaskORM.id)
        )
        demands = tuple(
            PortfolioDemandFact(
                resource_id=str(row.resource_id),
                task_id=str(row.task_id),
                project_id=str(row.project_id),
                project_name=str(row.project_name or row.project_id),
                start_date=row.start_date,
                end_date=row.end_date,
                allocation_percent=float(row.allocation_percent or 100.0),
            )
            for row in self._session.execute(demand_stmt)
        )
        return PortfolioResourcePoolFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            resources=resources,
            demands=demands,
        )


__all__ = ["SqlAlchemyPortfolioResourcePoolReader"]
