from __future__ import annotations

from src.core.platform.infrastructure.persistence.orm.sites import SiteORM
from src.core.platform.org.domain import Site


def site_to_orm(site: Site) -> SiteORM:
    return SiteORM(
        id=site.id,
        organization_id=site.organization_id,
        site_code=site.site_code,
        name=site.name,
        description=site.description or None,
        country=site.country or None,
        region=site.region or None,
        city=site.city or None,
        address_line_1=site.address_line_1 or None,
        address_line_2=site.address_line_2 or None,
        postal_code=site.postal_code or None,
        timezone=site.timezone or None,
        currency_code=site.currency_code or None,
        site_type=site.site_type or None,
        status=site.status or None,
        default_calendar_id=site.default_calendar_id or None,
        default_language=site.default_language or None,
        is_active=site.is_active,
        opened_at=site.opened_at,
        closed_at=site.closed_at,
        created_at=site.created_at,
        updated_at=site.updated_at,
        notes=site.notes or None,
        version=getattr(site, "version", 1),
    )


def site_from_orm(obj: SiteORM) -> Site:
    return Site(
        id=obj.id,
        organization_id=obj.organization_id,
        site_code=obj.site_code,
        name=obj.name,
        description=obj.description or "",
        country=obj.country or "",
        region=obj.region or "",
        city=obj.city or "",
        address_line_1=obj.address_line_1 or "",
        address_line_2=obj.address_line_2 or "",
        postal_code=obj.postal_code or "",
        timezone=obj.timezone or "",
        currency_code=obj.currency_code or "",
        site_type=obj.site_type or "",
        status=obj.status or "",
        default_calendar_id=obj.default_calendar_id or "",
        default_language=obj.default_language or "",
        is_active=obj.is_active,
        opened_at=obj.opened_at,
        closed_at=obj.closed_at,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "site_from_orm",
    "site_to_orm",
]
