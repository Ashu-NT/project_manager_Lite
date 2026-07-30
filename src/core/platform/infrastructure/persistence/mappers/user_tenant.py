from __future__ import annotations

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.infrastructure.persistence.orm.user_tenant import UserTenantORM
from src.core.platform.tenancy.domain.user_tenant_membership import UserTenantMembership


def user_tenant_to_orm(membership: UserTenantMembership) -> UserTenantORM:
    return UserTenantORM(
        id=membership.id,
        user_id=membership.user_id,
        tenant_id=membership.tenant_id,
        status=membership.status,
        is_active=membership.is_active,
        tenant_role=membership.tenant_role,
        invited_by_user_id=membership.invited_by_user_id,
        invited_at=membership.invited_at,
        invitation_expires_at=membership.invitation_expires_at,
        accepted_at=membership.accepted_at,
        joined_at=membership.joined_at,
        suspended_at=membership.suspended_at,
        revoked_at=membership.revoked_at,
        removed_at=membership.removed_at,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        version=membership.version,
    )


def user_tenant_from_orm(obj: UserTenantORM) -> UserTenantMembership:
    return UserTenantMembership(
        id=obj.id,
        user_id=obj.user_id,
        tenant_id=obj.tenant_id,
        status=obj.status,
        is_active=obj.is_active,
        tenant_role=obj.tenant_role,
        invited_by_user_id=obj.invited_by_user_id,
        invited_at=ensure_utc_datetime(obj.invited_at),
        invitation_expires_at=ensure_utc_datetime(obj.invitation_expires_at),
        accepted_at=ensure_utc_datetime(obj.accepted_at),
        joined_at=ensure_utc_datetime(obj.joined_at),
        suspended_at=ensure_utc_datetime(obj.suspended_at),
        revoked_at=ensure_utc_datetime(obj.revoked_at),
        removed_at=ensure_utc_datetime(obj.removed_at),
        created_at=ensure_utc_datetime(obj.created_at),
        updated_at=ensure_utc_datetime(obj.updated_at),
        version=obj.version,
    )


__all__ = ["user_tenant_from_orm", "user_tenant_to_orm"]
