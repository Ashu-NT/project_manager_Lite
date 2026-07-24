from __future__ import annotations

from src.core.platform.infrastructure.persistence.orm.tenant import TenantORM
from src.core.platform.tenancy.domain.tenant import TENANT_STATUS_ACTIVE, Tenant


def tenant_to_orm(tenant: Tenant) -> TenantORM:
    tenant_status = getattr(tenant, "tenant_status", TENANT_STATUS_ACTIVE) or TENANT_STATUS_ACTIVE
    return TenantORM(
        id=tenant.id,
        tenant_code=tenant.tenant_code,
        display_name=tenant.display_name,
        tenant_status=tenant_status,
        is_active=(tenant_status == TENANT_STATUS_ACTIVE),
        version=getattr(tenant, "version", 1),
    )


def tenant_from_orm(obj: TenantORM) -> Tenant:
    tenant_status = getattr(obj, "tenant_status", None) or TENANT_STATUS_ACTIVE
    return Tenant(
        id=obj.id,
        tenant_code=obj.tenant_code,
        display_name=obj.display_name,
        tenant_status=tenant_status,
        version=getattr(obj, "version", 1),
    )


__all__ = ["tenant_from_orm", "tenant_to_orm"]
