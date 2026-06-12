from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService


class TenantScopedRepositorySupport:
    _repository_label = "Repository"
    _tenant_context_service: TenantContextService | None

    def _context(self, *, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"{self._repository_label} requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )


__all__ = ["TenantScopedRepositorySupport"]
