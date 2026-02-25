from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import ResourceRepository
from core.models import Resource
from infra.db.models import ResourceORM
from infra.db.optimistic import update_with_version_check
from infra.db.resource.mapper import resource_from_orm, resource_to_orm


class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, resource: Resource) -> None:
        self.session.add(resource_to_orm(resource))

    def update(self, resource: Resource) -> None:
        resource.version = update_with_version_check(
            self.session,
            ResourceORM,
            resource.id,
            getattr(resource, "version", 1),
            {
                "name": resource.name,
                "role": resource.role,
                "hourly_rate": resource.hourly_rate,
                "is_active": resource.is_active,
                "cost_type": resource.cost_type,
                "currency_code": resource.currency_code,
            },
            not_found_message="Resource not found.",
            stale_message="Resource was updated by another user.",
        )

    def delete(self, resource_id: str) -> None:
        self.session.query(ResourceORM).filter_by(id=resource_id).delete()

    def get(self, resource_id: str) -> Optional[Resource]:
        obj = self.session.get(ResourceORM, resource_id)
        return resource_from_orm(obj) if obj else None

    def list_all(self) -> List[Resource]:
        stmt = select(ResourceORM)
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyResourceRepository"]
