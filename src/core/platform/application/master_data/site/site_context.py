from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.master_data.org import Organization

if TYPE_CHECKING:
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )


def active_organization(tenant_context_service: TenantContextService | None) -> Organization:
    if tenant_context_service is None:
        raise BusinessRuleError(
            "Active organization context is required.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    organization = tenant_context_service.get_active_organization()
    if organization is None:
        raise BusinessRuleError(
            "Active organization context is required.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    return organization


__all__ = ["active_organization"]
