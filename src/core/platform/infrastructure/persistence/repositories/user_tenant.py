from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.mappers.user_tenant import (
    user_tenant_from_orm,
    user_tenant_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.user_tenant import UserTenantORM
from src.core.platform.tenancy.contracts import UserTenantMembershipRepository
from src.core.platform.tenancy.domain.user_tenant_membership import (
    MEMBERSHIP_STATUS_ACTIVE,
    UserTenantMembership,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyUserTenantMembershipRepository(UserTenantMembershipRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, membership: UserTenantMembership) -> None:
        existing = self.get(membership.user_id, membership.tenant_id)
        if existing is not None:
            raise BusinessRuleError(
                "Tenant membership already exists; use an explicit lifecycle transition.",
                code="USER_TENANT_MEMBERSHIP_EXISTS",
            )
        self._session.add(user_tenant_to_orm(membership))

    def update(self, membership: UserTenantMembership) -> None:
        membership.version = update_with_version_check(
            self._session,
            UserTenantORM,
            membership.id,
            membership.version,
            {
                "status": membership.status,
                "is_active": membership.is_active,
                "tenant_role": membership.tenant_role,
                "invited_by_user_id": membership.invited_by_user_id,
                "invited_at": membership.invited_at,
                "invitation_expires_at": membership.invitation_expires_at,
                "accepted_at": membership.accepted_at,
                "joined_at": membership.joined_at,
                "suspended_at": membership.suspended_at,
                "revoked_at": membership.revoked_at,
                "removed_at": membership.removed_at,
                "updated_at": membership.updated_at,
            },
            not_found_message="Tenant membership not found.",
            stale_message="Tenant membership was updated by another process.",
            extra_filters={
                "user_id": membership.user_id,
                "tenant_id": membership.tenant_id,
            },
        )

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
            UserTenantORM.status == MEMBERSHIP_STATUS_ACTIVE,
            UserTenantORM.is_active.is_(True),
        )
        return self._session.execute(stmt).first() is not None

    def list_tenant_ids_for_user(self, user_id: str) -> list[str]:
        stmt = select(UserTenantORM.tenant_id).where(
            UserTenantORM.user_id == user_id,
            UserTenantORM.status == MEMBERSHIP_STATUS_ACTIVE,
            UserTenantORM.is_active.is_(True),
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_users_for_tenant(self, tenant_id: str) -> list[UserTenantMembership]:
        stmt = select(UserTenantORM).where(UserTenantORM.tenant_id == tenant_id)
        rows = self._session.execute(stmt).scalars().all()
        return [user_tenant_from_orm(row) for row in rows]

    def deactivate(self, user_id: str, tenant_id: str) -> None:
        membership = self.get(user_id, tenant_id)
        if membership is None or not membership.is_active:
            return
        self.update(membership.suspend())


__all__ = ["SqlAlchemyUserTenantMembershipRepository"]
