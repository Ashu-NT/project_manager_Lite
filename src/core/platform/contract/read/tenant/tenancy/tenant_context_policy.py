from __future__ import annotations

from enum import Enum
from typing import Protocol

from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    TenantRepository,
)
from src.core.platform.domain.tenant.tenancy.tenant import Tenant


class TenancyMode(str, Enum):
    SAAS = "saas"
    LOCAL_SINGLE_TENANT = "local_single_tenant"


class TenantContextPolicy(Protocol):
    mode: TenancyMode

    def resolve_active_tenant(
        self,
        *,
        session_tenant_id: str | None,
        tenant_repo: TenantRepository,
    ) -> Tenant | None: ...


__all__ = ["TenancyMode", "TenantContextPolicy"]
