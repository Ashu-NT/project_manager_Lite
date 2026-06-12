from __future__ import annotations

from src.core.platform.tenancy.domain.tenant import Tenant
from src.core.platform.infrastructure.persistence.orm.tenant import TenantORM


def tenant_to_orm(tenant: Tenant) -> TenantORM:
    return TenantORM(
        id=tenant.id,
        tenant_code=tenant.tenant_code,
        display_name=tenant.display_name,
        is_active=tenant.is_active,
        version=getattr(tenant, "version", 1),
    )


def tenant_from_orm(obj: TenantORM) -> Tenant:
    return Tenant(
        id=obj.id,
        tenant_code=obj.tenant_code,
        display_name=obj.display_name,
        is_active=obj.is_active,
        version=getattr(obj, "version", 1),
    )


__all__ = ["tenant_from_orm", "tenant_to_orm"]
