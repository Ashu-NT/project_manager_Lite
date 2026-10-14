from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.common.exceptions import ValidationError

if TYPE_CHECKING:
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )


def require_tenant_context_service(
    tenant_context_service: TenantContextService | None,
) -> TenantContextService:
    if tenant_context_service is None:
        raise ValidationError(
            "Active organization context is required.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    return tenant_context_service


def active_organization_id(
    tenant_context_service: TenantContextService | None, *, operation_label: str
) -> str:
    return require_tenant_context_service(tenant_context_service).require_active_organization_id(
        operation_label=operation_label,
    )


__all__ = ["active_organization_id", "require_tenant_context_service"]
