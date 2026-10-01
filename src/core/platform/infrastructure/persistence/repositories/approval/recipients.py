"""Bounded recipient projection over persisted request and effective scoped grants."""

from sqlalchemy import select

from src.core.platform.infrastructure.persistence.common.approval_eligibility import approval_reviewer_eligibility

from src.core.platform.infrastructure.persistence.common.scoped_permission import scoped_permission

from src.core.platform.infrastructure.persistence.orm.approval.approval import (
    ApprovalRequestORM,
)
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import (
    UserORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)


def recipient_page(
    session,
    *,
    request_id,
    tenant_id,
    organization_id,
    audience,
    after_user_id,
    limit,
    target_scope_predicate,
):
    if audience not in {"reviewers", "requester"}:
        raise ValueError("Unknown approval notification audience")
    request = ApprovalRequestORM
    authority = approval_reviewer_eligibility(UserORM.id) if audience == "reviewers" else scoped_permission(
        user_id=UserORM.id, tenant_id=request.tenant_id,
        organization_id=request.organization_id, project_id=request.project_id,
        permissions=("approval.request", "approval.decide"),
    )
    stmt = (
        select(UserORM.id)
        .join(UserTenantORM, UserTenantORM.user_id == UserORM.id)
        .join(request, request.tenant_id == UserTenantORM.tenant_id)
        .where(
            request.id == request_id,
            request.tenant_id == tenant_id,
            request.organization_id == organization_id,
            target_scope_predicate,
            UserORM.is_active.is_(True),
            UserORM.account_type == "human",
            UserTenantORM.status == "active",
            UserTenantORM.revoked_at.is_(None),
            UserORM.id > after_user_id,
            authority,
        )
    )
    if audience == "requester":
        stmt = stmt.where(UserORM.id == request.requested_by_user_id)
    return tuple(
        session.scalars(
            stmt.distinct().order_by(UserORM.id).limit(min(max(limit, 1), 100))
        )
    )
