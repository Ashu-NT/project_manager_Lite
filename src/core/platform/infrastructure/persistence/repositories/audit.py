from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditLogRepository
from src.core.platform.audit.domain import AuditLogEntry
from src.core.platform.infrastructure.persistence.mappers.audit import audit_from_orm, audit_to_orm
from src.core.platform.infrastructure.persistence.orm.audit import AuditLogORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)


class SqlAlchemyAuditLogRepository(TenantScopedRepositorySupport, AuditLogRepository):
    _repository_label = "AuditLogRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, entry: AuditLogEntry) -> None:
        ctx = self._context(operation_label="access audit log")
        orm = audit_to_orm(entry)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def list_recent(
        self,
        limit: int = 200,
        *,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> list[AuditLogEntry]:
        ctx = self._context(operation_label="access audit log")
        stmt = select(AuditLogORM).where(
            AuditLogORM.tenant_id == ctx.tenant_id,
            AuditLogORM.organization_id == ctx.organization_id,
        )
        if project_id is not None:
            stmt = stmt.where(AuditLogORM.project_id == project_id)
        if entity_type is not None:
            stmt = stmt.where(AuditLogORM.entity_type == entity_type)
        stmt = stmt.order_by(AuditLogORM.occurred_at.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [audit_from_orm(row) for row in rows]

    def list_recent_for_organization(
        self,
        organization_id: str,
        limit: int = 200,
        *,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> list[AuditLogEntry]:
        ctx = self._context(operation_label="access audit log")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(AuditLogORM).where(
            AuditLogORM.organization_id == ctx.organization_id,
            AuditLogORM.tenant_id == ctx.tenant_id,
        )
        if project_id is not None:
            stmt = stmt.where(AuditLogORM.project_id == project_id)
        if entity_type is not None:
            stmt = stmt.where(AuditLogORM.entity_type == entity_type)
        stmt = stmt.order_by(AuditLogORM.occurred_at.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [audit_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyAuditLogRepository"]
