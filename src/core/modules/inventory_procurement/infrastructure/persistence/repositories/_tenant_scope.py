from __future__ import annotations

from sqlalchemy import select

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.core.platform.tenancy.tenant_context import TenantContext


class InventoryTenantScopedRepositorySupport(TenantScopedRepositorySupport):
    _repository_label = "Inventory repository"

    @staticmethod
    def _tenant_in_scope(ctx: TenantContext, tenant_id: str | None) -> bool:
        active_tenant_id = getattr(ctx, "tenant_id", None)
        return active_tenant_id is None or tenant_id is None or tenant_id == active_tenant_id

    def _apply_scope(self, stmt, orm_model, ctx: TenantContext):
        organization_column = getattr(orm_model, "organization_id", None)
        if organization_column is not None:
            stmt = stmt.where(organization_column == ctx.organization_id)
        tenant_column = getattr(orm_model, "tenant_id", None)
        active_tenant_id = getattr(ctx, "tenant_id", None)
        if tenant_column is not None and active_tenant_id is not None:
            stmt = stmt.where(tenant_column == active_tenant_id)
        return stmt

    def _get_in_scope(self, orm_model, record_id: str, *, operation_label: str):
        ctx = self._context(operation_label=operation_label)
        stmt = self._apply_scope(
            select(orm_model).where(orm_model.id == record_id),
            orm_model,
            ctx,
        )
        return self.session.execute(stmt).scalars().first()

    def _require_in_scope(
        self,
        orm_model,
        record_id: str,
        *,
        operation_label: str,
        not_found_message: str,
    ):
        obj = self._get_in_scope(
            orm_model,
            record_id,
            operation_label=operation_label,
        )
        if obj is None:
            raise NotFoundError(not_found_message)
        return obj

    def _stamp_scope(self, ctx: TenantContext, orm: object) -> None:
        if hasattr(orm, "organization_id"):
            organization_id = getattr(orm, "organization_id", None)
            if organization_id is None:
                setattr(orm, "organization_id", ctx.organization_id)
            elif not self._organization_in_scope(ctx, organization_id):
                raise BusinessRuleError(
                    f"{self._repository_label} organization is outside the active scope.",
                    code="ORGANIZATION_SCOPE_VIOLATION",
                )
        if hasattr(orm, "tenant_id"):
            active_tenant_id = getattr(ctx, "tenant_id", None)
            tenant_id = getattr(orm, "tenant_id", None)
            if tenant_id is None and active_tenant_id is not None:
                setattr(orm, "tenant_id", active_tenant_id)
            elif not self._tenant_in_scope(ctx, tenant_id):
                raise BusinessRuleError(
                    f"{self._repository_label} tenant is outside the active scope.",
                    code="TENANT_SCOPE_VIOLATION",
                )


__all__ = ["InventoryTenantScopedRepositorySupport"]
