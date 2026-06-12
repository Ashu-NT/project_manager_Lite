from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)
from src.core.platform.access.domain import ProjectMembership, ScopedAccessGrant
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.orm.access import (
    ProjectMembershipORM,
    ScopedAccessGrantORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant import TenantORM


def _seed_access_scope_rows(services) -> dict[str, str]:
    session = services["session"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    auth_service = services["auth_service"]

    current_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="ACCESS-OPS",
        display_name="Access Operations",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )
    current_tenant_id = tenant_context_service.get_active_tenant_id()
    assert current_org is not None
    assert other_org is not None
    assert current_tenant_id is not None

    other_tenant = TenantORM(
        id="tenant-other-access",
        tenant_code="ACCESS-OTHER",
        display_name="Access Other Tenant",
        is_active=True,
        version=1,
    )
    user = auth_service.register_user(
        "access-scope-user",
        "StrongPass123",
        role_names=["viewer"],
    )
    now = datetime.now(timezone.utc)

    current_project = ProjectORM(
        id="project-current-access",
        tenant_id=current_tenant_id,
        organization_id=current_org.id,
        project_code="ACCESS-CUR",
        name="Current Access Project",
        description="",
        status=ProjectStatus.PLANNED,
        version=1,
    )
    other_project = ProjectORM(
        id="project-other-access",
        tenant_id=getattr(other_org, "tenant_id", None) or current_tenant_id,
        organization_id=other_org.id,
        project_code="ACCESS-OTH",
        name="Other Access Project",
        description="",
        status=ProjectStatus.PLANNED,
        version=1,
    )
    current_membership = ProjectMembershipORM(
        id="membership-current-access",
        project_id=current_project.id,
        user_id=user.id,
        organization_id=current_org.id,
        scope_role="viewer",
        permission_codes_json='["task.read"]',
        created_at=now,
    )
    other_membership = ProjectMembershipORM(
        id="membership-other-access",
        project_id=other_project.id,
        user_id=user.id,
        organization_id=other_org.id,
        scope_role="viewer",
        permission_codes_json='["task.read"]',
        created_at=now,
    )
    current_grant = ScopedAccessGrantORM(
        id="grant-current-access",
        tenant_id=current_tenant_id,
        scope_type="site",
        scope_id="site-current-access",
        user_id=user.id,
        scope_role="viewer",
        permission_codes_json='["site.read"]',
        created_at=now,
    )
    other_grant = ScopedAccessGrantORM(
        id="grant-other-access",
        tenant_id=other_tenant.id,
        scope_type="site",
        scope_id="site-other-access",
        user_id=user.id,
        scope_role="viewer",
        permission_codes_json='["site.read"]',
        created_at=now,
    )

    session.add(other_tenant)
    session.flush()
    session.add_all(
        [
            current_project,
            other_project,
            current_membership,
            other_membership,
        ]
    )
    session.flush()
    session.add_all([current_grant, other_grant])
    session.flush()
    return {
        "current_org_id": current_org.id,
        "other_org_id": other_org.id,
        "current_tenant_id": current_tenant_id,
        "user_id": user.id,
        "current_project_id": current_project.id,
        "other_project_id": other_project.id,
        "current_membership_id": current_membership.id,
        "other_membership_id": other_membership.id,
        "current_grant_id": current_grant.id,
        "other_grant_id": other_grant.id,
    }


def test_access_repositories_hide_cross_scope_rows(services) -> None:
    seeded = _seed_access_scope_rows(services)

    membership_repo = services["access_service"]._membership_repo
    grant_repo = services["access_service"]._scoped_access_repo

    assert membership_repo.get(seeded["other_membership_id"]) is None
    assert grant_repo.get(seeded["other_membership_id"]) is None
    assert grant_repo.get(seeded["other_grant_id"]) is None
    assert membership_repo.get(seeded["current_membership_id"]) is not None
    assert grant_repo.get(seeded["current_grant_id"]) is not None

    assert (
        membership_repo.get_for_project_user(
            seeded["other_project_id"],
            seeded["user_id"],
        )
        is None
    )
    assert (
        grant_repo.get_for_scope_user(
            "project",
            seeded["other_project_id"],
            seeded["user_id"],
        )
        is None
    )
    assert (
        grant_repo.get_for_scope_user(
            "site",
            "site-other-access",
            seeded["user_id"],
        )
        is None
    )

    membership_ids = {row.id for row in membership_repo.list_by_user(seeded["user_id"])}
    project_scope_ids = {
        row.id for row in grant_repo.list_by_scope("project", seeded["current_project_id"])
    }
    user_scope_ids = {row.id for row in grant_repo.list_by_user(seeded["user_id"])}

    assert membership_repo.list_by_project(seeded["other_project_id"]) == []
    assert grant_repo.list_by_scope("project", seeded["other_project_id"]) == []
    assert seeded["current_membership_id"] in membership_ids
    assert seeded["other_membership_id"] not in membership_ids
    assert seeded["current_membership_id"] in project_scope_ids
    assert seeded["other_membership_id"] not in project_scope_ids
    assert seeded["current_membership_id"] in user_scope_ids
    assert seeded["current_grant_id"] in user_scope_ids
    assert seeded["other_membership_id"] not in user_scope_ids
    assert seeded["other_grant_id"] not in user_scope_ids


def test_access_repositories_do_not_delete_foreign_scope_rows(services) -> None:
    seeded = _seed_access_scope_rows(services)
    session = services["session"]

    membership_repo = services["access_service"]._membership_repo
    grant_repo = services["access_service"]._scoped_access_repo

    grant_repo.delete(seeded["other_membership_id"])
    grant_repo.delete(seeded["other_grant_id"])
    membership_repo.delete(seeded["current_membership_id"])
    grant_repo.delete(seeded["current_grant_id"])
    session.flush()

    assert (
        session.get(ProjectMembershipORM, seeded["other_membership_id"]) is not None
    )
    assert session.get(ScopedAccessGrantORM, seeded["other_grant_id"]) is not None
    assert (
        session.get(ProjectMembershipORM, seeded["current_membership_id"]) is None
    )
    assert session.get(ScopedAccessGrantORM, seeded["current_grant_id"]) is None


def test_access_repositories_stamp_scope_metadata_and_reject_foreign_projects(
    services,
) -> None:
    seeded = _seed_access_scope_rows(services)
    session = services["session"]
    user = services["auth_service"].register_user(
        "access-scope-writer",
        "StrongPass123",
        role_names=["viewer"],
    )

    membership_repo = services["access_service"]._membership_repo
    grant_repo = services["access_service"]._scoped_access_repo

    membership = ProjectMembership.create(
        project_id=seeded["current_project_id"],
        user_id=user.id,
        scope_role="viewer",
        permission_codes=["task.read"],
    )
    grant = ScopedAccessGrant.create(
        scope_type="site",
        scope_id="site-write-access",
        user_id=user.id,
        scope_role="viewer",
        permission_codes=["site.read"],
    )

    membership_repo.add(membership)
    grant_repo.add(grant)
    session.flush()

    membership_row = session.get(ProjectMembershipORM, membership.id)
    grant_row = session.get(ScopedAccessGrantORM, grant.id)

    assert membership_row is not None
    assert grant_row is not None
    assert membership_row.organization_id == seeded["current_org_id"]
    assert grant_row.tenant_id == seeded["current_tenant_id"]

    with pytest.raises(NotFoundError, match="Project not found"):
        membership_repo.add(
            ProjectMembership.create(
                project_id=seeded["other_project_id"],
                user_id=user.id,
                scope_role="viewer",
                permission_codes=["task.read"],
            )
        )
    with pytest.raises(NotFoundError, match="Project not found"):
        grant_repo.add(
            ScopedAccessGrant.create(
                scope_type="project",
                scope_id=seeded["other_project_id"],
                user_id=user.id,
                scope_role="viewer",
                permission_codes=["task.read"],
            )
        )
