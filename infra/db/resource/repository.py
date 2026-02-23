from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import ResourceRepository
from core.models import Resource
from infra.db.models import ResourceORM
from infra.db.resource.mapper import resource_from_orm, resource_to_orm


class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, resource: Resource) -> None:
        self.session.add(resource_to_orm(resource))

    def update(self, resource: Resource) -> None:
        self.session.merge(resource_to_orm(resource))

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
