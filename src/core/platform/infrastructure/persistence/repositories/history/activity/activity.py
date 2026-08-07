from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.contract.history.activity.contracts import ActivityRepository
from src.core.platform.domain.history.activity.activity_entry import ActivityEntry
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.mappers.history.activity.activity import activity_from_orm, activity_to_orm
from src.core.platform.infrastructure.persistence.orm.history.activity.activity import ActivityEntryORM
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
        ctx = self._context(operation_label="record activity")
        orm = activity_to_orm(entry)
        self._stamp_scope(ctx, orm)
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
        parent_entity_id: str | None = None,
        action_prefix: str | None = None,
    ) -> list[ActivityEntry]:
        ctx = self._context(operation_label="list activity")
        if tenant_id is not None and tenant_id != ctx.tenant_id:
            raise BusinessRuleError(
                "Activity tenant is outside the active scope.",
                code="TENANT_SCOPE_VIOLATION",
            )
        if organization_id is not None and organization_id != ctx.organization_id:
            raise BusinessRuleError(
                "Activity organization is outside the active scope.",
                code="ORGANIZATION_SCOPE_VIOLATION",
            )
        stmt = self._apply_scope(select(ActivityEntryORM), ActivityEntryORM, ctx)
        if entity_type is not None:
            stmt = stmt.where(ActivityEntryORM.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(ActivityEntryORM.entity_id == entity_id)
        if module is not None:
            stmt = stmt.where(ActivityEntryORM.module == module)
        if workspace_id is not None:
            stmt = stmt.where(ActivityEntryORM.workspace_id == workspace_id)
        if parent_entity_id is not None:
            stmt = stmt.where(ActivityEntryORM.parent_entity_id == parent_entity_id)
        if action_prefix is not None:
            stmt = stmt.where(ActivityEntryORM.action.startswith(action_prefix))
        stmt = stmt.order_by(ActivityEntryORM.timestamp.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [activity_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyActivityRepository"]
