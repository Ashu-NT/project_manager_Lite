"""Concrete, tenant/organization-scoped single-query reads backing Platform
Overview's cross-entity counts.

One dedicated read-side adapter per entity's aggregate, not the write
repositories' ``list_for_organization`` fully hydrating every row just to
compute a handful of integers (and, for Sites, three sampled names).
``OrganizationService``/``SiteService``/``DepartmentService``/
``PartyService``/``DocumentService`` each depend on
``PlatformOverviewRollupReader`` (``contract/read/overview/
platform_overview_rollup_reader.py``), never on this concrete class
directly, matching the ``SqlAlchemyEmployeeHeadcountReader`` precedent.
"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DepartmentRollupSummary,
    DocumentRollupSummary,
    PartyRollupSummary,
    SiteRollupSummary,
)
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.master_data.documents.documents import DocumentORM
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
from src.core.platform.infrastructure.persistence.orm.master_data.party.party import PartyORM
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM


class SqlAlchemyPlatformOverviewRollupReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_organization_count(self, *, tenant_id: str) -> int:
        total = self._session.execute(
            select(func.count(OrganizationORM.id)).where(OrganizationORM.tenant_id == tenant_id)
        ).scalar_one()
        return int(total or 0)

    def get_site_summary(
        self,
        *,
        organization_id: str,
        tenant_id: str,
        allowed_site_ids: frozenset[str] | None = None,
    ) -> SiteRollupSummary:
        if allowed_site_ids is not None and not allowed_site_ids:
            # Scope-restricted caller with zero permitted sites -- matches
            # filter_scope_rows() returning [] without issuing a query.
            return SiteRollupSummary(total=0, active=0, sample_names=())

        conditions = [
            SiteORM.organization_id == organization_id,
            SiteORM.tenant_id == tenant_id,
        ]
        if allowed_site_ids is not None:
            conditions.append(SiteORM.id.in_(allowed_site_ids))

        total, active = self._session.execute(
            select(
                func.count(SiteORM.id),
                func.sum(case((SiteORM.is_active.is_(True), 1), else_=0)),
            ).where(*conditions)
        ).one()

        # Matches SqlAlchemySiteRepository.list_for_organization's
        # .order_by(SiteORM.name.asc()) ordering exactly, so the sampled
        # names are the same first-3-alphabetically today's admin_overview_
        # presenter.py gets from sites[:3] after that same ordered fetch.
        sample_names = self._session.execute(
            select(SiteORM.name).where(*conditions).order_by(SiteORM.name.asc()).limit(3)
        ).scalars().all()

        return SiteRollupSummary(
            total=int(total or 0),
            active=int(active or 0),
            sample_names=tuple(sample_names),
        )

    def get_department_summary(self, *, organization_id: str, tenant_id: str) -> DepartmentRollupSummary:
        total, active = self._session.execute(
            select(
                func.count(DepartmentORM.id),
                func.sum(case((DepartmentORM.is_active.is_(True), 1), else_=0)),
            ).where(
                DepartmentORM.organization_id == organization_id,
                DepartmentORM.tenant_id == tenant_id,
            )
        ).one()
        return DepartmentRollupSummary(total=int(total or 0), active=int(active or 0))

    def get_party_summary(self, *, organization_id: str, tenant_id: str) -> PartyRollupSummary:
        total, active = self._session.execute(
            select(
                func.count(PartyORM.id),
                func.sum(case((PartyORM.is_active.is_(True), 1), else_=0)),
            ).where(
                PartyORM.organization_id == organization_id,
                PartyORM.tenant_id == tenant_id,
            )
        ).one()
        return PartyRollupSummary(total=int(total or 0), active=int(active or 0))

    def get_document_summary(self, *, organization_id: str, tenant_id: str) -> DocumentRollupSummary:
        total, current = self._session.execute(
            select(
                func.count(DocumentORM.id),
                func.sum(case((DocumentORM.is_current.is_(True), 1), else_=0)),
            ).where(
                DocumentORM.organization_id == organization_id,
                DocumentORM.tenant_id == tenant_id,
            )
        ).one()
        return DocumentRollupSummary(total=int(total or 0), current=int(current or 0))


__all__ = ["SqlAlchemyPlatformOverviewRollupReader"]
