from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditRepository
from src.core.platform.audit.domain.audit_entry import AuditEntry
from src.core.platform.infrastructure.persistence.mappers.audit_entry import (
    audit_entry_from_orm,
    audit_entry_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.audit_entry import AuditEntryORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)


class SqlAlchemyAuditRepository(TenantScopedRepositorySupport, AuditRepository):
    _repository_label = "AuditRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, entry: AuditEntry) -> None:
        ctx = self._context(operation_label="record audit entry")
        orm = audit_entry_to_orm(entry)
        orm.tenant_id = orm.tenant_id or ctx.tenant_id
        orm.organization_id = orm.organization_id or ctx.organization_id
        self.session.add(orm)

    def list_recent(
        self,
        limit: int = 100,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
        compliance_tag: str | None = None,
    ) -> list[AuditEntry]:
        ctx = self._context(operation_label="list audit entries")
        stmt = select(AuditEntryORM).where(
            AuditEntryORM.tenant_id == ctx.tenant_id,
            AuditEntryORM.organization_id == ctx.organization_id,
        )
        if entity_type is not None:
            stmt = stmt.where(AuditEntryORM.entity_type == entity_type)
        if operation is not None:
            stmt = stmt.where(AuditEntryORM.operation == operation)
        if severity is not None:
            stmt = stmt.where(AuditEntryORM.severity == severity)
        if compliance_tag is not None:
            stmt = stmt.where(AuditEntryORM.compliance_tag == compliance_tag)
        stmt = stmt.order_by(AuditEntryORM.timestamp.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [audit_entry_from_orm(row) for row in rows]

    def list_recent_for_organization(
        self,
        organization_id: str,
        limit: int = 100,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
    ) -> list[AuditEntry]:
        ctx = self._context(operation_label="list audit entries for organization")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(AuditEntryORM).where(
            AuditEntryORM.organization_id == organization_id,
            AuditEntryORM.tenant_id == ctx.tenant_id,
        )
        if entity_type is not None:
            stmt = stmt.where(AuditEntryORM.entity_type == entity_type)
        if operation is not None:
            stmt = stmt.where(AuditEntryORM.operation == operation)
        if severity is not None:
            stmt = stmt.where(AuditEntryORM.severity == severity)
        stmt = stmt.order_by(AuditEntryORM.timestamp.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [audit_entry_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyAuditRepository"]
