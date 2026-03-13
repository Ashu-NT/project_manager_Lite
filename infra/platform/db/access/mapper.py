from __future__ import annotations

import json

from core.platform.common.models import ProjectMembership
from infra.platform.db.models import ProjectMembershipORM


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


__all__ = ["project_membership_from_orm", "project_membership_to_orm"]
