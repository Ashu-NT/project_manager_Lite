from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.master_data.site.sites import site_from_orm, site_to_orm
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.core.platform.contract.repositories.master_data.site.contracts import SiteRepository
from src.core.platform.domain.master_data.site import SITE_STATUS_ACTIVE, Site
from src.infra.persistence.db.optimistic import update_with_version_check


def _active_only_condition(active_only: bool):
    # active_only has no separate physical column to filter on -- status is
    # the only lifecycle source of truth (see Site.is_active, a computed
    # property, never a stored duplicate). False means "not active",
    # matching the historic boolean semantics (lumps inactive + archived).
    if active_only:
        return SiteORM.status == SITE_STATUS_ACTIVE
    return SiteORM.status != SITE_STATUS_ACTIVE


class SqlAlchemySiteRepository(TenantScopedRepositorySupport, SiteRepository):
    _repository_label = "SiteRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, site: Site) -> None:
        ctx = self._context(operation_label="access sites")
        orm = site_to_orm(site)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def update(self, site: Site) -> None:
        ctx = self._context(operation_label="access sites")
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
                "opened_at": site.opened_at,
                "closed_at": site.closed_at,
                "created_at": site.created_at,
                "updated_at": site.updated_at,
                "notes": site.notes or None,
            },
            extra_filters={
                "tenant_id": ctx.tenant_id,
                "organization_id": ctx.organization_id,
            },
            not_found_message="Site not found.",
            stale_message="Site was updated by another user.",
        )

    def get(self, site_id: str) -> Site | None:
        ctx = self._context(operation_label="access sites")
        stmt = select(SiteORM).where(
            SiteORM.id == site_id,
            SiteORM.tenant_id == ctx.tenant_id,
            SiteORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return site_from_orm(obj) if obj else None

    def get_for_tenant(self, site_id: str, tenant_id: str) -> Site | None:
        stmt = select(SiteORM).where(
            SiteORM.id == site_id,
            SiteORM.tenant_id == tenant_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return site_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, site_code: str) -> Site | None:
        ctx = self._context(operation_label="access sites")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(SiteORM).where(
            SiteORM.organization_id == ctx.organization_id,
            SiteORM.site_code == site_code,
            SiteORM.tenant_id == ctx.tenant_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return site_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Site]:
        ctx = self._context(operation_label="access sites")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(SiteORM).where(
            SiteORM.organization_id == ctx.organization_id,
            SiteORM.tenant_id == ctx.tenant_id,
        )
        if active_only is not None:
            stmt = stmt.where(_active_only_condition(active_only))
        rows = self.session.execute(stmt.order_by(SiteORM.name.asc())).scalars().all()
        return [site_from_orm(row) for row in rows]

    def list_page_for_organization_in_tenant(
        self,
        organization_id: str,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        active_only: bool | None = None,
    ) -> tuple[list[Site], int, int]:
        # Deliberately bypasses self._context()/_organization_in_scope() --
        # both organization_id and tenant_id are caller-supplied and trusted
        # (the service layer verifies the organization actually belongs to
        # this tenant before calling here), not the session's ambient active
        # organization. See get_for_tenant() for the same pattern.
        base_condition = (
            SiteORM.organization_id == organization_id,
            SiteORM.tenant_id == tenant_id,
        )
        total = self.session.execute(
            select(func.count()).select_from(SiteORM).where(*base_condition)
        ).scalar_one()

        filtered_stmt = select(SiteORM).where(*base_condition)
        filtered_count_stmt = select(func.count()).select_from(SiteORM).where(*base_condition)
        if active_only is not None:
            condition = _active_only_condition(active_only)
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            condition = or_(
                SiteORM.name.ilike(pattern),
                SiteORM.site_code.ilike(pattern),
                SiteORM.city.ilike(pattern),
                SiteORM.country.ilike(pattern),
            )
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)

        filtered_total = self.session.execute(filtered_count_stmt).scalar_one()
        offset = max(0, (page - 1) * page_size)
        rows = self.session.execute(
            filtered_stmt.order_by(SiteORM.name.asc()).offset(offset).limit(page_size)
        ).scalars().all()
        return [site_from_orm(row) for row in rows], total, filtered_total


__all__ = [
    "SqlAlchemySiteRepository",
]
