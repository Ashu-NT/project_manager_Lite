from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditLogRepository
from src.core.platform.audit.domain import AuditLogEntry
from src.core.platform.infrastructure.persistence.mappers.audit import audit_from_orm, audit_to_orm
from src.core.platform.infrastructure.persistence.orm.audit import AuditLogORM


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def _get_active_tid(self) -> str | None:
        return self._tenant_context_service.get_active_tenant_id() if self._tenant_context_service else None

    def add(self, entry: AuditLogEntry) -> None:
        orm = audit_to_orm(entry)
        if orm.tenant_id is None:
            orm.tenant_id = self._get_active_tid()
        self.session.add(orm)

    def list_recent(
        self,
        limit: int = 200,
        *,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> list[AuditLogEntry]:
        _tid = self._get_active_tid()
        stmt = select(AuditLogORM)
        if _tid is not None:
            stmt = stmt.where(AuditLogORM.tenant_id == _tid)
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
        _tid = self._get_active_tid()
        stmt = select(AuditLogORM).where(AuditLogORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(AuditLogORM.tenant_id == _tid)
        if project_id is not None:
            stmt = stmt.where(AuditLogORM.project_id == project_id)
        if entity_type is not None:
            stmt = stmt.where(AuditLogORM.entity_type == entity_type)
        stmt = stmt.order_by(AuditLogORM.occurred_at.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [audit_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyAuditLogRepository"]
