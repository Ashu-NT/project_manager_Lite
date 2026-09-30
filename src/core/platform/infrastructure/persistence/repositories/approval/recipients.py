"""Bounded recipient projection over persisted request and effective scoped grants."""

from datetime import datetime, timezone

from sqlalchemy import and_, or_, select

from src.core.platform.infrastructure.persistence.orm.approval.approval import ApprovalRequestORM
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import (
    PermissionORM,
    RoleBindingORM,
    RoleORM,
    RolePermissionORM,
    UserORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import UserTenantORM


def recipient_page(session, *, request_id, tenant_id, organization_id, audience, after_user_id, limit):
    if audience not in {"reviewers", "requester"}:
        raise ValueError("Unknown approval notification audience")
    request = ApprovalRequestORM
    binding = RoleBindingORM
    now = datetime.now(timezone.utc)
    covered_scope = or_(
        binding.actual_scope_type == "tenant",
        and_(binding.actual_scope_type == "organization", binding.actual_scope_id == request.organization_id),
        and_(binding.actual_scope_type == "project", binding.actual_scope_id == request.project_id),
    )
    authority = (
        select(binding.id)
        .join(RoleORM, RoleORM.id == binding.role_id)
        .join(RolePermissionORM, RolePermissionORM.role_id == RoleORM.id)
        .join(PermissionORM, PermissionORM.id == RolePermissionORM.permission_id)
        .where(
            binding.principal_type == "user", binding.principal_id == UserORM.id,
            binding.tenant_id == request.tenant_id, binding.revoked_at.is_(None),
            or_(binding.expires_at.is_(None), binding.expires_at > now),
            RoleORM.allowed_scope_type == binding.actual_scope_type,
            RoleORM.status == "active",
            or_(RoleORM.tenant_id.is_(None), RoleORM.tenant_id == request.tenant_id),
            PermissionORM.code.in_(("approval.decide",) if audience == "reviewers"
                                   else ("approval.request", "approval.decide")),
            covered_scope,
        ).correlate(UserORM, request).exists()
    )
    stmt = (
        select(UserORM.id)
        .join(UserTenantORM, UserTenantORM.user_id == UserORM.id)
        .join(request, request.tenant_id == UserTenantORM.tenant_id)
        .where(
            request.id == request_id, request.tenant_id == tenant_id,
            request.organization_id == organization_id,
            UserORM.is_active.is_(True), UserORM.account_type == "human",
            UserTenantORM.status == "active", UserTenantORM.revoked_at.is_(None),
            UserORM.id > after_user_id, authority,
        )
    )
    if audience == "reviewers":
        stmt = stmt.where(
            request.status == "PENDING",
            or_(request.requested_by_user_id.is_(None), UserORM.id != request.requested_by_user_id),
        )
    else:
        stmt = stmt.where(UserORM.id == request.requested_by_user_id)
    return tuple(session.scalars(stmt.distinct().order_by(UserORM.id).limit(min(max(limit, 1), 100))))
