from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import false, or_, select
from sqlalchemy.orm import Session

from src.core.platform.contract.repositories.history.audit.contracts import AuditRepository
from src.core.platform.domain.history.audit.audit_entry import AuditEntry
from src.core.platform.infrastructure.persistence.mappers.history.audit.audit_entry import (
    audit_entry_from_orm,
    audit_entry_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import AuditEntryORM
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

    def add_for_tenant(self, entry: AuditEntry, tenant_id: str) -> None:
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            raise ValueError("Explicit tenant audit scope is required.")
        if entry.tenant_id != normalized_tenant_id:
            raise ValueError("Audit entry tenant does not match its explicit scope.")
        self.session.add(audit_entry_to_orm(entry))

    def add_platform(self, entry: AuditEntry) -> None:
        if entry.tenant_id is not None or entry.organization_id is not None:
            raise ValueError("Platform audit entries cannot carry customer tenant context.")
        self.session.add(audit_entry_to_orm(entry))

    def list_recent(
        self,
        limit: int = 100,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
        compliance_tag: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
        operation_prefixes: Sequence[str] | None = None,
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
        stmt = self._apply_projection_filters(
            stmt,
            module=module,
            workspace_id=workspace_id,
            operation_prefixes=operation_prefixes,
        )
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
        module: str | None = None,
        workspace_id: str | None = None,
        operation_prefixes: Sequence[str] | None = None,
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
        stmt = self._apply_projection_filters(
            stmt,
            module=module,
            workspace_id=workspace_id,
            operation_prefixes=operation_prefixes,
        )
        stmt = stmt.order_by(AuditEntryORM.timestamp.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [audit_entry_from_orm(row) for row in rows]

    @staticmethod
    def _apply_projection_filters(
        stmt,
        *,
        module: str | None,
        workspace_id: str | None,
        operation_prefixes: Sequence[str] | None,
    ):
        if module is not None:
            stmt = stmt.where(AuditEntryORM.module == module)
        if workspace_id is not None:
            stmt = stmt.where(AuditEntryORM.workspace_id == workspace_id)
        if operation_prefixes is not None:
            prefixes = tuple(
                str(prefix).strip() for prefix in operation_prefixes if str(prefix).strip()
            )
            stmt = stmt.where(
                or_(*(AuditEntryORM.operation.startswith(prefix) for prefix in prefixes))
                if prefixes
                else false()
            )
        return stmt


__all__ = ["SqlAlchemyAuditRepository"]
