from __future__ import annotations

from core.models import Resource
from infra.db.models import ResourceORM


def resource_to_orm(resource: Resource) -> ResourceORM:
    return ResourceORM(
        id=resource.id,
        name=resource.name,
        role=resource.role,
        hourly_rate=resource.hourly_rate,
        is_active=resource.is_active,
        cost_type=resource.cost_type,
        currency_code=resource.currency_code,
        version=getattr(resource, "version", 1),
    )


def resource_from_orm(obj: ResourceORM) -> Resource:
    return Resource(
        id=obj.id,
        name=obj.name,
        role=obj.role,
        hourly_rate=obj.hourly_rate,
        is_active=obj.is_active,
        cost_type=obj.cost_type,
        currency_code=obj.currency_code,
        version=getattr(obj, "version", 1),
    )


__all__ = ["resource_to_orm", "resource_from_orm"]
