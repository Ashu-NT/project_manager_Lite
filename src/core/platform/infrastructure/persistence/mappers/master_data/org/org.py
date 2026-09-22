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
        status=organization.status,
        version=getattr(organization, "version", 1),
        legal_name=organization.legal_name,
        registration_number=organization.registration_number,
        tax_id=organization.tax_id,
        address_line_1=organization.address_line_1,
        address_line_2=organization.address_line_2,
        postal_code=organization.postal_code,
        city=organization.city,
        state_region=organization.state_region,
        country_code=organization.country_code,
        email=organization.email,
        phone=organization.phone,
        website=organization.website,
    )


def organization_from_orm(obj: OrganizationORM) -> Organization:
    return Organization(
        id=obj.id,
        tenant_id=getattr(obj, "tenant_id", None),
        organization_code=obj.organization_code,
        display_name=obj.display_name,
        timezone_name=obj.timezone_name,
        base_currency=obj.base_currency,
        status=obj.status,
        version=getattr(obj, "version", 1),
        legal_name=getattr(obj, "legal_name", "") or "",
        registration_number=getattr(obj, "registration_number", "") or "",
        tax_id=getattr(obj, "tax_id", "") or "",
        address_line_1=getattr(obj, "address_line_1", "") or "",
        address_line_2=getattr(obj, "address_line_2", "") or "",
        postal_code=getattr(obj, "postal_code", "") or "",
        city=getattr(obj, "city", "") or "",
        state_region=getattr(obj, "state_region", "") or "",
        country_code=getattr(obj, "country_code", "") or "",
        email=getattr(obj, "email", "") or "",
        phone=getattr(obj, "phone", "") or "",
        website=getattr(obj, "website", "") or "",
    )


__all__ = [
    "organization_from_orm",
    "organization_to_orm",
]
