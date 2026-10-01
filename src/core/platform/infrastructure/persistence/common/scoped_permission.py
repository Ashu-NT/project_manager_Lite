"""SQL eligibility projection over the canonical scoped RBAC tables."""

from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import aliased

from src.core.platform.infrastructure.persistence.orm.security.auth.auth import (
    PermissionORM,
    RoleBindingORM,
    RoleORM,
    RolePermissionORM,
    UserORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)


def scoped_permission(*, user_id, tenant_id, organization_id, project_id=None, permissions):
    user, member = aliased(UserORM), aliased(UserTenantORM)
    binding, role = aliased(RoleBindingORM), aliased(RoleORM)
    role_permission, permission = aliased(RolePermissionORM), aliased(PermissionORM)
    scopes = [binding.actual_scope_type == "tenant",
              and_(binding.actual_scope_type == "organization", binding.actual_scope_id == organization_id)]
    if project_id is not None:
        scopes.append(and_(binding.actual_scope_type == "project", binding.actual_scope_id == project_id))
    return (select(binding.id).select_from(binding)
            .join(user, user.id == binding.principal_id)
            .join(member, and_(member.user_id == user.id, member.tenant_id == tenant_id))
            .join(role, role.id == binding.role_id)
            .join(role_permission, role_permission.role_id == role.id)
            .join(permission, permission.id == role_permission.permission_id)
            .where(user.id == user_id, user.is_active.is_(True), user.account_type == "human",
                   member.status == "active", member.revoked_at.is_(None),
                   binding.principal_type == "user", binding.tenant_id == tenant_id,
                   binding.revoked_at.is_(None),
                   or_(binding.expires_at.is_(None), binding.expires_at > datetime.now(timezone.utc)),
                   role.status == "active", role.allowed_scope_type == binding.actual_scope_type,
                   or_(role.tenant_id.is_(None), role.tenant_id == tenant_id),
                   permission.code.in_(permissions), or_(*scopes))
            .correlate_except(user, member, binding, role, role_permission, permission).exists())
