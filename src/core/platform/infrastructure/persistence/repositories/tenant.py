from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.tenant import tenant_from_orm, tenant_to_orm
from src.core.platform.infrastructure.persistence.orm.tenant import TenantORM
from src.core.platform.tenancy.contracts import TenantRepository
from src.core.platform.tenancy.domain.tenant import Tenant
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyTenantRepository(TenantRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, tenant: Tenant) -> None:
        self._session.add(tenant_to_orm(tenant))

    def update(self, tenant: Tenant) -> None:
        tenant.version = update_with_version_check(
            self._session,
            TenantORM,
            tenant.id,
            getattr(tenant, "version", 1),
            {
                "tenant_code": tenant.tenant_code,
                "display_name": tenant.display_name,
                "is_active": tenant.is_active,
            },
            not_found_message="Tenant not found.",
            stale_message="Tenant was updated by another process.",
        )

    def get(self, tenant_id: str) -> Tenant | None:
        obj = self._session.get(TenantORM, tenant_id)
        return tenant_from_orm(obj) if obj else None

    def get_by_code(self, tenant_code: str) -> Tenant | None:
        stmt = select(TenantORM).where(TenantORM.tenant_code == str(tenant_code or "").strip().upper())
        obj = self._session.execute(stmt).scalars().first()
        return tenant_from_orm(obj) if obj else None

    def get_default(self) -> Tenant | None:
        stmt = select(TenantORM).where(TenantORM.is_active.is_(True)).order_by(TenantORM.tenant_code.asc())
        obj = self._session.execute(stmt).scalars().first()
        return tenant_from_orm(obj) if obj else None

    def list_all(self, *, active_only: bool | None = None) -> list[Tenant]:
        stmt = select(TenantORM)
        if active_only is not None:
            stmt = stmt.where(TenantORM.is_active == bool(active_only))
        rows = self._session.execute(stmt.order_by(TenantORM.display_name.asc())).scalars().all()
        return [tenant_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyTenantRepository"]
