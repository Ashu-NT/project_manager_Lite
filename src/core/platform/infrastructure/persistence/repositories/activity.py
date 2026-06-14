from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.activity.contracts import ActivityRepository
from src.core.platform.activity.domain.activity_entry import ActivityEntry
from src.core.platform.infrastructure.persistence.mappers.activity import activity_from_orm, activity_to_orm
from src.core.platform.infrastructure.persistence.orm.activity import ActivityEntryORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)


class SqlAlchemyActivityRepository(TenantScopedRepositorySupport, ActivityRepository):
    _repository_label = "ActivityRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, entry: ActivityEntry) -> None:
        orm = activity_to_orm(entry)
        self.session.add(orm)

    def list_recent(
        self,
        limit: int = 200,
        *,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
    ) -> list[ActivityEntry]:
        stmt = select(ActivityEntryORM)
        if tenant_id is not None:
            stmt = stmt.where(ActivityEntryORM.tenant_id == tenant_id)
        if organization_id is not None:
            stmt = stmt.where(ActivityEntryORM.organization_id == organization_id)
        if entity_type is not None:
            stmt = stmt.where(ActivityEntryORM.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(ActivityEntryORM.entity_id == entity_id)
        if module is not None:
            stmt = stmt.where(ActivityEntryORM.module == module)
        if workspace_id is not None:
            stmt = stmt.where(ActivityEntryORM.workspace_id == workspace_id)
        stmt = stmt.order_by(ActivityEntryORM.timestamp.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [activity_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyActivityRepository"]
