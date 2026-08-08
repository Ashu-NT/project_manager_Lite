from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql import Select

from src.core.modules.project_management.infrastructure.persistence.orm.cost import CostItemORM
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)

SqlSelect = Select[tuple[Any, ...]]

def _project_scope(*, tenant_id: str, organization_id: str, project_id: str)-> ColumnElement[bool]:
    return and_(
        ProjectORM.id == project_id,
        ProjectORM.tenant_id == tenant_id,
        ProjectORM.organization_id == organization_id,
    )


def project_fact_statement(*, tenant_id: str, organization_id: str, project_id: str) -> SqlSelect:
    return select(
        ProjectORM.id,
        ProjectORM.tenant_id,
        ProjectORM.organization_id,
        ProjectORM.currency,
        ProjectORM.planned_budget,
        ProjectORM.start_date,
        ProjectORM.end_date,
    ).where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))


def task_facts_statement(*, tenant_id: str, organization_id: str, project_id: str)-> SqlSelect:
    return (
        select(
            TaskORM.id,
            TaskORM.name,
            TaskORM.start_date,
            TaskORM.end_date,
            TaskORM.actual_start,
            TaskORM.actual_end,
        )
        .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
        .order_by(TaskORM.id)
    )


def cost_item_facts_statement(*, tenant_id: str, organization_id: str, project_id: str)-> SqlSelect:
    return (
        select(
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
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
        .order_by(CostItemORM.id)
    )


def cost_aggregate_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, as_of: date
)-> SqlSelect:
    actual_in_scope = or_(CostItemORM.incurred_date.is_(None), CostItemORM.incurred_date <= as_of)
    dimensions = (
        CostItemORM.cost_type,
        CostItemORM.currency_code,
        CostItemORM.commitment_status,
    )
    return (
        select(
            *dimensions,
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
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
        .group_by(*dimensions)
        .order_by(*dimensions)
    )


def project_resource_facts_statement(*, tenant_id: str, organization_id: str, project_id: str) -> SqlSelect:
    return (
        select(
            ProjectResourceORM.id,
            ProjectResourceORM.resource_id,
            ProjectResourceORM.planned_hours,
            ProjectResourceORM.is_active,
        )
        .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
        .order_by(ProjectResourceORM.id)
    )


def assignment_facts_statement(*, tenant_id: str, organization_id: str, project_id: str) -> SqlSelect:
    return (
        select(
            TaskAssignmentORM.id,
            TaskAssignmentORM.task_id,
            TaskAssignmentORM.resource_id,
            TaskAssignmentORM.hours_logged,
        )
        .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
        .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
        .order_by(TaskAssignmentORM.id)
    )


def resource_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, resource_ids: tuple[str, ...]
)-> SqlSelect:
    project_resource_exists = select(ProjectResourceORM.id).join(
        ProjectORM, ProjectORM.id == ProjectResourceORM.project_id
    ).where(
        ProjectResourceORM.resource_id == ResourceORM.id,
        _project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id),
    ).exists()
    assignment_exists = select(TaskAssignmentORM.id).join(
        TaskORM, TaskORM.id == TaskAssignmentORM.task_id
    ).join(ProjectORM, ProjectORM.id == TaskORM.project_id).where(
        TaskAssignmentORM.resource_id == ResourceORM.id,
        _project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id),
    ).exists()
    return (
        select(ResourceORM.id, ResourceORM.name, ResourceORM.is_active)
        .where(
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
            ResourceORM.id.in_(resource_ids),
            or_(project_resource_exists, assignment_exists),
        )
        .order_by(ResourceORM.id)
    )


__all__ = [
    "assignment_facts_statement",
    "cost_aggregate_facts_statement",
    "cost_item_facts_statement",
    "project_fact_statement",
    "project_resource_facts_statement",
    "resource_facts_statement",
    "task_facts_statement",
]

