from __future__ import annotations

from src.core.platform.domain.master_data.org import Organization
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM


def organization_to_orm(organization: Organization) -> OrganizationORM:
    return OrganizationORM(
        id=organization.id,
        tenant_id=getattr(organization, "tenant_id", None),
        organization_code=organization.organization_code,
        display_name=organization.display_name,
        timezone_name=organization.timezone_name,
        base_currency=organization.base_currency,
        is_enabled=organization.is_enabled,
        version=getattr(organization, "version", 1),
    )


def organization_from_orm(obj: OrganizationORM) -> Organization:
    return Organization(
        id=obj.id,
        tenant_id=getattr(obj, "tenant_id", None),
        organization_code=obj.organization_code,
        display_name=obj.display_name,
        timezone_name=obj.timezone_name,
        base_currency=obj.base_currency,
        is_enabled=obj.is_enabled,
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "organization_from_orm",
    "organization_to_orm",
]
