from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.user_tenant import (
    user_tenant_from_orm,
    user_tenant_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.user_tenant import UserTenantORM
from src.core.platform.tenancy.contracts import UserTenantMembershipRepository
from src.core.platform.tenancy.domain.user_tenant_membership import UserTenantMembership


class SqlAlchemyUserTenantMembershipRepository(UserTenantMembershipRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, membership: UserTenantMembership) -> None:
        existing = self.get(membership.user_id, membership.tenant_id)
        if existing is not None:
            return
        self._session.add(user_tenant_to_orm(membership))

    def get(self, user_id: str, tenant_id: str) -> UserTenantMembership | None:
        stmt = select(UserTenantORM).where(
            UserTenantORM.user_id == user_id,
            UserTenantORM.tenant_id == tenant_id,
        )
        obj = self._session.execute(stmt).scalars().first()
        return user_tenant_from_orm(obj) if obj else None

    def is_active_member(self, user_id: str, tenant_id: str) -> bool:
        stmt = select(UserTenantORM.id).where(
            UserTenantORM.user_id == user_id,
            UserTenantORM.tenant_id == tenant_id,
            UserTenantORM.is_active.is_(True),
        )
        return self._session.execute(stmt).first() is not None

    def list_tenant_ids_for_user(self, user_id: str) -> list[str]:
        stmt = select(UserTenantORM.tenant_id).where(
            UserTenantORM.user_id == user_id,
            UserTenantORM.is_active.is_(True),
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_users_for_tenant(self, tenant_id: str) -> list[UserTenantMembership]:
        stmt = select(UserTenantORM).where(UserTenantORM.tenant_id == tenant_id)
        rows = self._session.execute(stmt).scalars().all()
        return [user_tenant_from_orm(row) for row in rows]

    def deactivate(self, user_id: str, tenant_id: str) -> None:
        obj = self._session.execute(
            select(UserTenantORM).where(
                UserTenantORM.user_id == user_id,
                UserTenantORM.tenant_id == tenant_id,
            )
        ).scalars().first()
        if obj is not None:
            obj.is_active = False
            obj.updated_at = datetime.now(timezone.utc)


__all__ = ["SqlAlchemyUserTenantMembershipRepository"]
