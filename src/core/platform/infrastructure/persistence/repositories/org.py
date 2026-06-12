from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.org import (
    organization_from_orm,
    organization_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.org import OrganizationORM
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyOrganizationRepository(OrganizationRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, organization: Organization) -> None:
        self.session.add(organization_to_orm(organization))

    def update(self, organization: Organization) -> None:
        organization.version = update_with_version_check(
            self.session,
            OrganizationORM,
            organization.id,
            getattr(organization, "version", 1),
            {
                "tenant_id": getattr(organization, "tenant_id", None),
                "organization_code": organization.organization_code,
                "display_name": organization.display_name,
                "timezone_name": organization.timezone_name,
                "base_currency": organization.base_currency,
                "is_active": organization.is_active,
            },
            not_found_message="Organization not found.",
            stale_message="Organization was updated by another user.",
        )

    def get(self, organization_id: str) -> Organization | None:
        obj = self.session.get(OrganizationORM, organization_id)
        return organization_from_orm(obj) if obj else None

    def get_by_code(self, organization_code: str) -> Organization | None:
        stmt = select(OrganizationORM).where(OrganizationORM.organization_code == organization_code)
        obj = self.session.execute(stmt).scalars().first()
        return organization_from_orm(obj) if obj else None

    def get_active(self) -> Organization | None:
        stmt = select(OrganizationORM).where(OrganizationORM.is_active.is_(True))
        obj = self.session.execute(stmt.order_by(OrganizationORM.display_name.asc())).scalars().first()
        return organization_from_orm(obj) if obj else None

    def list_all(self, *, active_only: bool | None = None) -> list[Organization]:
        stmt = select(OrganizationORM)
        if active_only is not None:
            stmt = stmt.where(OrganizationORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(OrganizationORM.display_name.asc())).scalars().all()
        return [organization_from_orm(row) for row in rows]

    def list_for_tenant(self, tenant_id: str, *, active_only: bool | None = None) -> list[Organization]:
        stmt = select(OrganizationORM).where(OrganizationORM.tenant_id == tenant_id)
        if active_only is not None:
            stmt = stmt.where(OrganizationORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(OrganizationORM.display_name.asc())).scalars().all()
        return [organization_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyOrganizationRepository",
]
