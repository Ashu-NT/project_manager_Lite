from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.resources import (
    ResourceWorkloadDemandFact,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)


class SqlAlchemyResourceWorkloadDemandReader:
    """Bounded assignment demand for one scoped Resource and date range."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_overlapping_assignments(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        start_date: date,
        end_date: date,
    ) -> tuple[ResourceWorkloadDemandFact, ...]:
        rows = self._session.execute(
            select(
                TaskAssignmentORM.id,
                TaskAssignmentORM.task_id,
                TaskORM.project_id,
                TaskORM.start_date,
                TaskORM.end_date,
                TaskAssignmentORM.allocation_percent,
                TaskAssignmentORM.allocated_planned_hours,
            )
            .select_from(TaskAssignmentORM)
            .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .join(ResourceORM, ResourceORM.id == TaskAssignmentORM.resource_id)
            .where(
                TaskAssignmentORM.resource_id == resource_id,
                ResourceORM.tenant_id == tenant_id,
                ResourceORM.organization_id == organization_id,
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
                TaskORM.start_date.is_not(None),
                TaskORM.end_date.is_not(None),
                TaskORM.start_date <= end_date,
                TaskORM.end_date >= start_date,
            )
            .order_by(TaskORM.start_date.asc(), TaskAssignmentORM.id.asc())
        ).all()
        return tuple(
            ResourceWorkloadDemandFact(
                assignment_id=str(row[0]),
                task_id=str(row[1]),
                project_id=str(row[2]),
                task_start=row[3],
                task_end=row[4],
                allocation_percent=Decimal(str(row[5] or 0)),
                allocated_planned_hours=Decimal(str(row[6] or 0)),
            )
            for row in rows
        )


__all__ = ["SqlAlchemyResourceWorkloadDemandReader"]
