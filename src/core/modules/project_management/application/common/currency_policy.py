from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.finance.money.currency_resolution import resolve_currency_code


def resolve_pm_currency(
    *,
    tenant_context_service,
    operation_label: str,
    explicit: str | None = None,
    project_default: str | None = None,
) -> str:
    """Resolve a PM transaction currency from authorized organization context."""
    if tenant_context_service is None:
        raise BusinessRuleError(
            f"Active organization context is required for {operation_label}.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    organization = tenant_context_service.get_active_organization()
    if organization is None:
        raise BusinessRuleError(
            f"Active organization context is required for {operation_label}.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    return resolve_currency_code(
        explicit=explicit,
        project_default=project_default,
        organization_default=organization.base_currency,
    ).currency.code


__all__ = ["resolve_pm_currency"]
