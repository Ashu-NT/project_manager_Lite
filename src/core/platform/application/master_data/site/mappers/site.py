from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.application.master_data.site.queries.site_queries import (
        SitePage,
    )
    from src.core.platform.domain.master_data.site import Site

from src.core.platform.application.master_data.site.dto.responses.site import (
    SiteDto,
    SitePageDto,
)


def serialize_site_page(page: SitePage) -> SitePageDto:
    return SitePageDto(
        items=tuple(serialize_site(site) for site in page.items),
        total=page.total,
        filtered_total=page.filtered_total,
        page=page.page,
        page_size=page.page_size,
    )




def serialize_site(site: Site) -> SiteDto:
    return SiteDto(
        id=site.id,
        organization_id=site.organization_id,
        site_code=site.site_code,
        name=site.name,
        description=site.description,
        country=site.country,
        region=site.region,
        city=site.city,
        address_line_1=site.address_line_1,
        address_line_2=site.address_line_2,
        postal_code=site.postal_code,
        timezone=site.timezone,
        currency_code=site.currency_code,
        site_type=site.site_type,
        status=site.status,
        default_calendar_id=site.default_calendar_id,
        default_language=site.default_language,
        is_active=site.is_active,
        notes=site.notes,
        version=site.version,
        opened_at=site.opened_at,
        closed_at=site.closed_at,
        created_at=site.created_at,
        updated_at=site.updated_at,
    )
