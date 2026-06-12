from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.register import RegisterEntryRepository
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.register import RegisterEntryORM
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.register import register_entry_from_orm, register_entry_to_orm


class SqlAlchemyRegisterEntryRepository(RegisterEntryRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "RegisterEntryRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label="access register entries"
        )

    def _project_scoped_stmt(self):
        ctx = self._context()
        return (
            select(RegisterEntryORM)
            .join(ProjectORM, RegisterEntryORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def _ensure_project_in_scope(self, project_id: str) -> None:
        ctx = self._context()
        project = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.")

    def add(self, entry: RegisterEntry) -> None:
        self._ensure_project_in_scope(entry.project_id)
        self.session.add(register_entry_to_orm(entry))

    def update(self, entry: RegisterEntry) -> None:
        if self.get(entry.id) is None:
            raise BusinessRuleError("Register entry not found.")
        self._ensure_project_in_scope(entry.project_id)
        entry.version = update_with_version_check(
            self.session,
            RegisterEntryORM,
            entry.id,
            getattr(entry, "version", 1),
            {
                "project_id": entry.project_id,
                "entry_type": entry.entry_type,
                "title": entry.title,
                "description": entry.description,
                "severity": entry.severity,
                "status": entry.status,
                "owner_name": entry.owner_name,
                "due_date": entry.due_date,
                "impact_summary": entry.impact_summary,
                "response_plan": entry.response_plan,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
            },
            extra_filters={"project_id": entry.project_id},
            not_found_message="Register entry not found.",
            stale_message="Register entry was updated by another user.",
        )

    def delete(self, entry_id: str) -> None:
        self.session.execute(
            RegisterEntryORM.__table__.delete().where(
                RegisterEntryORM.id.in_(
                    self._project_scoped_stmt()
                    .where(RegisterEntryORM.id == entry_id)
                    .with_only_columns(RegisterEntryORM.id)
                )
            )
        )

    def get(self, entry_id: str) -> RegisterEntry | None:
        stmt = self._project_scoped_stmt().where(RegisterEntryORM.id == entry_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return register_entry_from_orm(row) if row else None

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[RegisterEntry]:
        stmt = self._project_scoped_stmt()
        if project_id:
            stmt = stmt.where(RegisterEntryORM.project_id == project_id)
        if entry_type is not None:
            stmt = stmt.where(RegisterEntryORM.entry_type == entry_type)
        if status is not None:
            stmt = stmt.where(RegisterEntryORM.status == status)
        if severity is not None:
            stmt = stmt.where(RegisterEntryORM.severity == severity)
        stmt = stmt.order_by(
            RegisterEntryORM.due_date.is_(None),
            RegisterEntryORM.due_date.asc(),
            RegisterEntryORM.updated_at.desc(),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [register_entry_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyRegisterEntryRepository"]
