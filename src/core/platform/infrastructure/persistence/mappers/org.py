from __future__ import annotations

from src.core.platform.org.domain import Organization
from src.core.platform.infrastructure.persistence.orm.org import OrganizationORM


def organization_to_orm(organization: Organization) -> OrganizationORM:
    return OrganizationORM(
        id=organization.id,
        organization_code=organization.organization_code,
        display_name=organization.display_name,
        timezone_name=organization.timezone_name,
        base_currency=organization.base_currency,
        is_active=organization.is_active,
        version=getattr(organization, "version", 1),
    )


def organization_from_orm(obj: OrganizationORM) -> Organization:
    return Organization(
        id=obj.id,
        organization_code=obj.organization_code,
        display_name=obj.display_name,
        timezone_name=obj.timezone_name,
        base_currency=obj.base_currency,
        is_active=obj.is_active,
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "organization_from_orm",
    "organization_to_orm",
]
