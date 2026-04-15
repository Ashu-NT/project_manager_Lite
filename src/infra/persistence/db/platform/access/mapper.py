from __future__ import annotations

import json

from core.platform.access.domain import ProjectMembership, ScopedAccessGrant
from src.infra.persistence.orm.platform.models import ProjectMembershipORM, ScopedAccessGrantORM


def project_membership_to_orm(membership: ProjectMembership) -> ProjectMembershipORM:
    return ProjectMembershipORM(
        id=membership.id,
        project_id=membership.project_id,
        user_id=membership.user_id,
        scope_role=membership.scope_role,
        permission_codes_json=json.dumps(list(membership.permission_codes or [])),
        created_at=membership.created_at,
    )


def project_membership_from_orm(obj: ProjectMembershipORM) -> ProjectMembership:
    try:
        permission_codes = json.loads(obj.permission_codes_json or "[]")
    except Exception:
        permission_codes = []
    return ProjectMembership(
        id=obj.id,
        project_id=obj.project_id,
        user_id=obj.user_id,
        scope_role=obj.scope_role,
        permission_codes=[str(item).strip() for item in permission_codes if str(item).strip()],
        created_at=obj.created_at,
    )


def scoped_access_grant_to_orm(grant: ScopedAccessGrant) -> ProjectMembershipORM | ScopedAccessGrantORM:
    if (grant.scope_type or "").strip().lower() == "project":
        return project_membership_to_orm(ProjectMembership.from_scoped_access_grant(grant))
    return ScopedAccessGrantORM(
        id=grant.id,
        scope_type=grant.scope_type,
        scope_id=grant.scope_id,
        user_id=grant.user_id,
        scope_role=grant.scope_role,
        permission_codes_json=json.dumps(list(grant.permission_codes or [])),
        created_at=grant.created_at,
    )


def scoped_access_grant_from_orm(obj: ProjectMembershipORM | ScopedAccessGrantORM) -> ScopedAccessGrant:
    if isinstance(obj, ProjectMembershipORM):
        return project_membership_from_orm(obj).as_scoped_access_grant()
    try:
        permission_codes = json.loads(obj.permission_codes_json or "[]")
    except Exception:
        permission_codes = []
    return ScopedAccessGrant(
        id=obj.id,
        scope_type=obj.scope_type,
        scope_id=obj.scope_id,
        user_id=obj.user_id,
        scope_role=obj.scope_role,
        permission_codes=[str(item).strip() for item in permission_codes if str(item).strip()],
        created_at=obj.created_at,
    )


__all__ = [
    "project_membership_from_orm",
    "project_membership_to_orm",
    "scoped_access_grant_from_orm",
    "scoped_access_grant_to_orm",
]
