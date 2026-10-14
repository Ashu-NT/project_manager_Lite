from __future__ import annotations

from src.core.platform.contract.read.tenant.tenancy.tenant_context_policy import (
    TenancyMode,
    TenantContextPolicy,
)
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    TenantRepository,
)
from src.core.platform.domain.tenant.tenancy.tenant import Tenant


def _resolve_session_tenant(
    session_tenant_id: str | None,
    tenant_repo: TenantRepository,
) -> Tenant | None:
    normalized_tenant_id = str(session_tenant_id or "").strip()
    if not normalized_tenant_id:
        return None
    tenant = tenant_repo.get(normalized_tenant_id)
    if tenant is None or not tenant.is_active:
        return None
    return tenant


class SaaSTenantContextPolicy:
    mode = TenancyMode.SAAS

    def resolve_active_tenant(
        self,
        *,
        session_tenant_id: str | None,
        tenant_repo: TenantRepository,
    ) -> Tenant | None:
        return _resolve_session_tenant(session_tenant_id, tenant_repo)


class LocalSingleTenantContextPolicy:
    mode = TenancyMode.LOCAL_SINGLE_TENANT

    def resolve_active_tenant(
        self,
        *,
        session_tenant_id: str | None,
        tenant_repo: TenantRepository,
    ) -> Tenant | None:
        tenant = _resolve_session_tenant(session_tenant_id, tenant_repo)
        if tenant is not None:
            return tenant
        fallback = tenant_repo.get_default()
        if fallback is None or not fallback.is_active:
            return None
        return fallback


def build_tenant_context_policy(mode: TenancyMode) -> TenantContextPolicy:
    if mode is TenancyMode.SAAS:
        return SaaSTenantContextPolicy()
    if mode is TenancyMode.LOCAL_SINGLE_TENANT:
        return LocalSingleTenantContextPolicy()
    raise ValueError(f"Unsupported tenancy mode: {mode!r}")


__all__ = [
    "LocalSingleTenantContextPolicy",
    "SaaSTenantContextPolicy",
    "TenancyMode",
    "build_tenant_context_policy",
]
