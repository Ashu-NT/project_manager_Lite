from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.sites import site_from_orm, site_to_orm
from src.core.platform.infrastructure.persistence.orm.sites import SiteORM
from src.core.platform.org.contracts import SiteRepository
from src.core.platform.org.domain import Site
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemySiteRepository(SiteRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, site: Site) -> None:
        self.session.add(site_to_orm(site))

    def update(self, site: Site) -> None:
        site.version = update_with_version_check(
            self.session,
            SiteORM,
            site.id,
            getattr(site, "version", 1),
            {
                "site_code": site.site_code,
                "name": site.name,
                "description": site.description or None,
                "country": site.country or None,
                "region": site.region or None,
                "city": site.city or None,
                "address_line_1": site.address_line_1 or None,
                "address_line_2": site.address_line_2 or None,
                "postal_code": site.postal_code or None,
                "timezone": site.timezone or None,
                "currency_code": site.currency_code or None,
                "site_type": site.site_type or None,
                "status": site.status or None,
                "default_calendar_id": site.default_calendar_id or None,
                "default_language": site.default_language or None,
                "is_active": site.is_active,
                "opened_at": site.opened_at,
                "closed_at": site.closed_at,
                "created_at": site.created_at,
                "updated_at": site.updated_at,
                "notes": site.notes or None,
            },
            not_found_message="Site not found.",
            stale_message="Site was updated by another user.",
        )

    def get(self, site_id: str) -> Optional[Site]:
        obj = self.session.get(SiteORM, site_id)
        return site_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, site_code: str) -> Optional[Site]:
        stmt = select(SiteORM).where(
            SiteORM.organization_id == organization_id,
            SiteORM.site_code == site_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return site_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> List[Site]:
        stmt = select(SiteORM).where(SiteORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(SiteORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(SiteORM.name.asc())).scalars().all()
        return [site_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemySiteRepository",
]
