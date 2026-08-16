
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DepartmentRollupSummary,
    DocumentRollupSummary,
    PartyRollupSummary,
    SiteRollupSummary,
    UserRollupSummary,
)
from src.core.platform.domain.security.authorization.roles import ROLE_SCOPE_PLATFORM
from src.core.platform.domain.tenant.tenancy.user_tenant_membership import MEMBERSHIP_STATUS_ACTIVE
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.master_data.documents.documents import DocumentORM
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
from src.core.platform.infrastructure.persistence.orm.master_data.party.party import PartyORM
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import RoleBindingORM, RoleORM, UserORM
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import UserTenantORM

# Must stay in sync with PLATFORM_ROLE_NAMES in
# application/security/authorization/roles/role_scope_policy.py -- not
# imported directly since this infrastructure/read module must not depend
# on the application layer.
_PLATFORM_ROLE_NAMES = ("admin", "support_admin")


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

    def get_user_summary(self, *, tenant_id: str | None) -> UserRollupSummary:
        if tenant_id is None:
            # Platform-operator caller: SqlAlchemyUserRepository.list_all()'s
            # exact population -- every user, no tenant filter, no exclusion.
            total, active, locked = self._session.execute(
                select(
                    func.count(UserORM.id),
                    func.sum(case((UserORM.is_active.is_(True), 1), else_=0)),
                    func.sum(case((UserORM.locked_until.is_not(None), 1), else_=0)),
                )
            ).one()
            return UserRollupSummary(total=int(total or 0), active=int(active or 0), locked=int(locked or 0))

        now = datetime.now(timezone.utc)
        has_platform_authority = (
            select(1)
            .select_from(RoleBindingORM)
            .join(RoleORM, RoleORM.id == RoleBindingORM.role_id)
            .where(
                RoleBindingORM.principal_type == "user",
                RoleBindingORM.principal_id == UserORM.id,
                RoleBindingORM.actual_scope_type == ROLE_SCOPE_PLATFORM,
                RoleORM.allowed_scope_type == ROLE_SCOPE_PLATFORM,
                RoleBindingORM.revoked_at.is_(None),
                or_(RoleBindingORM.expires_at.is_(None), RoleBindingORM.expires_at > now),
                RoleORM.status == "active",
                func.lower(RoleORM.name).in_(_PLATFORM_ROLE_NAMES),
            )
            .exists()
        )

        total, active, locked = self._session.execute(
            select(
                func.count(UserORM.id),
                func.sum(case((UserORM.is_active.is_(True), 1), else_=0)),
                func.sum(case((UserORM.locked_until.is_not(None), 1), else_=0)),
            )
            .select_from(UserORM)
            .join(UserTenantORM, UserTenantORM.user_id == UserORM.id)
            .where(
                UserTenantORM.tenant_id == tenant_id,
                UserTenantORM.status == MEMBERSHIP_STATUS_ACTIVE,
                ~has_platform_authority,
            )
        ).one()
        return UserRollupSummary(total=int(total or 0), active=int(active or 0), locked=int(locked or 0))


__all__ = ["SqlAlchemyPlatformOverviewRollupReader"]
