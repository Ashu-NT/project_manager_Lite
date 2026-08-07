from __future__ import annotations

from sqlalchemy import select

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContext,
    TenantContextService,
)


class TenantScopedRepositorySupport:
    _repository_label = "Repository"
    _tenant_context_service: TenantContextService | None

    def _context(self, *, operation_label: str) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"{self._repository_label} requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    def _tenant_context(self, *, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"{self._repository_label} requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_context(
            operation_label=operation_label
        )

    @staticmethod
    def _organization_in_scope(
        ctx: TenantContext,
        organization_id: str | None,
    ) -> bool:
        return bool(organization_id) and organization_id == ctx.organization_id

    @staticmethod
    def _tenant_in_scope(ctx: TenantContext, tenant_id: str | None) -> bool:
        return bool(tenant_id) and tenant_id == ctx.tenant_id

    def _apply_scope(self, stmt, orm_model, ctx: TenantContext):
        organization_column = getattr(orm_model, "organization_id", None)
        if organization_column is not None:
            stmt = stmt.where(organization_column == ctx.organization_id)
        tenant_column = getattr(orm_model, "tenant_id", None)
        if tenant_column is not None:
            stmt = stmt.where(tenant_column == ctx.tenant_id)
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
            if not organization_id:
                setattr(orm, "organization_id", ctx.organization_id)
            elif organization_id != ctx.organization_id:
                raise BusinessRuleError(
                    f"{self._repository_label} organization is outside the active scope.",
                    code="ORGANIZATION_SCOPE_VIOLATION",
                )
        if hasattr(orm, "tenant_id"):
            tenant_id = getattr(orm, "tenant_id", None)
            if not tenant_id:
                setattr(orm, "tenant_id", ctx.tenant_id)
            elif not self._tenant_in_scope(ctx, tenant_id):
                raise BusinessRuleError(
                    f"{self._repository_label} tenant is outside the active scope.",
                    code="TENANT_SCOPE_VIOLATION",
                )


class TenantParentScopedRepositorySupport(TenantScopedRepositorySupport):
    def _scoped_stmt_for_anchor(
        self,
        row_model,
        anchor_model,
        *,
        joins: tuple[tuple[object, object], ...],
        operation_label: str,
    ):
        ctx = self._context(operation_label=operation_label)
        stmt = select(row_model)
        for join_model, on_clause in joins:
            stmt = stmt.join(join_model, on_clause)
        return self._apply_scope(stmt, anchor_model, ctx)

    def _get_via_anchor_in_scope(
        self,
        row_model,
        anchor_model,
        *,
        joins: tuple[tuple[object, object], ...],
        record_id: str,
        operation_label: str,
    ):
        stmt = self._scoped_stmt_for_anchor(
            row_model,
            anchor_model,
            joins=joins,
            operation_label=operation_label,
        ).where(row_model.id == record_id)
        return self.session.execute(stmt).scalars().first()

    def _require_via_anchor_in_scope(
        self,
        row_model,
        anchor_model,
        *,
        joins: tuple[tuple[object, object], ...],
        record_id: str,
        operation_label: str,
        not_found_message: str,
    ):
        obj = self._get_via_anchor_in_scope(
            row_model,
            anchor_model,
            joins=joins,
            record_id=record_id,
            operation_label=operation_label,
        )
        if obj is None:
            raise NotFoundError(not_found_message)
        return obj

    def _require_anchor_in_scope(
        self,
        anchor_model,
        anchor_id: str,
        *,
        operation_label: str,
        not_found_message: str,
        joins: tuple[tuple[object, object], ...] = (),
        scope_model=None,
    ):
        ctx = self._context(operation_label=operation_label)
        stmt = select(anchor_model)
        for join_model, on_clause in joins:
            stmt = stmt.join(join_model, on_clause)
        stmt = self._apply_scope(stmt, scope_model or anchor_model, ctx).where(
            anchor_model.id == anchor_id
        )
        obj = self.session.execute(stmt).scalars().first()
        if obj is None:
            raise NotFoundError(not_found_message)
        return obj


__all__ = [
    "TenantParentScopedRepositorySupport",
    "TenantScopedRepositorySupport",
]
