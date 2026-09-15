from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.master_data.org.org import (
    organization_from_orm,
    organization_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
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
                "is_enabled": organization.is_enabled,
                "legal_name": organization.legal_name,
                "registration_number": organization.registration_number,
                "tax_id": organization.tax_id,
                "address_line_1": organization.address_line_1,
                "address_line_2": organization.address_line_2,
                "postal_code": organization.postal_code,
                "city": organization.city,
                "state_region": organization.state_region,
                "country_code": organization.country_code,
                "email": organization.email,
                "phone": organization.phone,
                "website": organization.website,
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

    def get_for_tenant(self, organization_id: str, tenant_id: str) -> Organization | None:
        stmt = (
            select(OrganizationORM)
            .where(OrganizationORM.id == organization_id)
            .where(OrganizationORM.tenant_id == tenant_id)
        )
        obj = self.session.execute(stmt).scalars().first()
        return organization_from_orm(obj) if obj else None

    def get_by_code_for_tenant(self, organization_code: str, tenant_id: str) -> Organization | None:
        stmt = (
            select(OrganizationORM)
            .where(OrganizationORM.organization_code == organization_code)
            .where(OrganizationORM.tenant_id == tenant_id)
        )
        obj = self.session.execute(stmt).scalars().first()
        return organization_from_orm(obj) if obj else None

    def list_all(self, *, enabled_only: bool | None = None) -> list[Organization]:
        stmt = select(OrganizationORM)
        if enabled_only is not None:
            stmt = stmt.where(OrganizationORM.is_enabled == bool(enabled_only))
        rows = self.session.execute(stmt.order_by(OrganizationORM.display_name.asc())).scalars().all()
        return [organization_from_orm(row) for row in rows]

    def list_for_tenant(self, tenant_id: str, *, enabled_only: bool | None = None) -> list[Organization]:
        stmt = select(OrganizationORM).where(OrganizationORM.tenant_id == tenant_id)
        if enabled_only is not None:
            stmt = stmt.where(OrganizationORM.is_enabled == bool(enabled_only))
        rows = self.session.execute(stmt.order_by(OrganizationORM.display_name.asc())).scalars().all()
        return [organization_from_orm(row) for row in rows]

    def list_page_for_tenant(
        self,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        enabled_only: bool | None = None,
    ) -> tuple[list[Organization], int, int]:
        total = self.session.execute(
            select(func.count())
            .select_from(OrganizationORM)
            .where(OrganizationORM.tenant_id == tenant_id)
        ).scalar_one()

        filtered_stmt = select(OrganizationORM).where(OrganizationORM.tenant_id == tenant_id)
        filtered_count_stmt = (
            select(func.count())
            .select_from(OrganizationORM)
            .where(OrganizationORM.tenant_id == tenant_id)
        )
        if enabled_only is not None:
            condition = OrganizationORM.is_enabled == bool(enabled_only)
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            condition = or_(
                OrganizationORM.display_name.ilike(pattern),
                OrganizationORM.organization_code.ilike(pattern),
            )
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)

        filtered_total = self.session.execute(filtered_count_stmt).scalar_one()
        offset = max(0, (page - 1) * page_size)
        rows = self.session.execute(
            filtered_stmt.order_by(OrganizationORM.display_name.asc()).offset(offset).limit(page_size)
        ).scalars().all()
        return [organization_from_orm(row) for row in rows], total, filtered_total


__all__ = [
    "SqlAlchemyOrganizationRepository",
]
