from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditLogRepository
from src.core.platform.audit.domain import AuditLogEntry
from src.core.platform.infrastructure.persistence.mappers.audit import audit_from_orm, audit_to_orm
from src.core.platform.infrastructure.persistence.orm.audit import AuditLogORM


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, entry: AuditLogEntry) -> None:
        self.session.add(audit_to_orm(entry))

    def list_recent(
        self,
        limit: int = 200,
        *,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> List[AuditLogEntry]:
        stmt = select(AuditLogORM)
        if project_id is not None:
            stmt = stmt.where(AuditLogORM.project_id == project_id)
        if entity_type is not None:
            stmt = stmt.where(AuditLogORM.entity_type == entity_type)
        stmt = stmt.order_by(AuditLogORM.occurred_at.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [audit_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyAuditLogRepository"]

