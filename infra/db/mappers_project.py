from __future__ import annotations

from core.models import Project, ProjectResource
from infra.db.models import ProjectORM, ProjectResourceORM


def project_to_orm(project: Project) -> ProjectORM:
    return ProjectORM(
        id=project.id,
        name=project.name,
        description=project.description,
        start_date=project.start_date,
        end_date=project.end_date,
        status=project.status,
        client_name=project.client_name,
        client_contact=project.client_contact,
        planned_budget=project.planned_budget,
        currency=project.currency,
    )


def project_from_orm(obj: ProjectORM) -> Project:
    return Project(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        start_date=obj.start_date,
        end_date=obj.end_date,
        status=obj.status,
        client_name=obj.client_name,
        client_contact=obj.client_contact,
        planned_budget=obj.planned_budget,
        currency=obj.currency,
    )


def project_resource_from_orm(obj: ProjectResourceORM) -> ProjectResource:
    return ProjectResource(
        id=obj.id,
        project_id=obj.project_id,
        resource_id=obj.resource_id,
        hourly_rate=obj.hourly_rate,
        currency_code=obj.currency_code,
        planned_hours=obj.planned_hours,
        is_active=obj.is_active,
    )


def project_resource_to_orm(resource: ProjectResource) -> ProjectResourceORM:
    return ProjectResourceORM(
        id=resource.id,
        project_id=resource.project_id,
        resource_id=resource.resource_id,
        hourly_rate=resource.hourly_rate,
        currency_code=resource.currency_code,
        planned_hours=resource.planned_hours,
        is_active=resource.is_active,
    )


__all__ = [
    "project_to_orm",
    "project_from_orm",
    "project_resource_from_orm",
    "project_resource_to_orm",
]
