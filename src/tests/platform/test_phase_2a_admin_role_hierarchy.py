"""Tests for Phase 2A: RBAC & Admin Role Hierarchy.

Covers:
  1. Policy unit: DEFAULT_ROLE_PERMISSIONS contains tenant_admin and org_admin
  2. Policy unit: tenant_admin has the correct permission set
  3. Policy unit: org_admin has the correct permission set
  4. Policy unit: tenant_admin does NOT have platform.admin
  5. Policy unit: org_admin does NOT have tenant.create or platform.admin
  6. Policy unit: all permissions in tenant_admin and org_admin are registered in DEFAULT_PERMISSIONS
  7. Integration: tenant_admin and org_admin roles are seeded in DB after bootstrap
  8. Integration: a user assigned tenant_admin gets correct permissions via build_principal
  9. Integration: a user assigned org_admin gets correct permissions via build_principal
  10. Integration: is_platform_admin() returns True for admin, False for tenant_admin/org_admin users
  11. Integration: org_admin binding accepts organization_id scope (Phase 0 constraint supports it)
"""
from __future__ import annotations

import pytest

from src.core.platform.domain.security.authorization.roles import RoleBinding
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
)


def _active_context_ids(services) -> tuple[str, str]:
    tenant_context = services["tenant_context_service"]
    tenant_id = tenant_context.get_active_tenant_id()
    organization_id = tenant_context.get_active_organization_id()
    assert tenant_id is not None
    assert organization_id is not None
    return tenant_id, organization_id


def _bind_org_role(services, user_id: str, organization_id: str, role_name: str) -> None:
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name(role_name)
    assert role is not None
    auth._role_binding_repo.add(
        RoleBinding.create(
            principal_id=user_id,
            role_id=role.id,
            tenant_id=services[
                "tenant_context_service"
            ].get_active_tenant_id(),
            actual_scope_type="organization",
            actual_scope_id=organization_id,
        )
    )
    services["session"].flush()


def _bind_org_admin(services, user_id: str, organization_id: str) -> None:
    _bind_org_role(services, user_id, organization_id, "org_admin")


# ---------------------------------------------------------------------------
# 1–6. Policy-level unit tests (no DB required)
# ---------------------------------------------------------------------------

def test_tenant_admin_role_is_defined_in_policy():
    assert "tenant_admin" in DEFAULT_ROLE_PERMISSIONS


def test_org_admin_role_is_defined_in_policy():
    assert "org_admin" in DEFAULT_ROLE_PERMISSIONS


def test_tenant_admin_has_customer_tenant_permissions_only():
    perms = DEFAULT_ROLE_PERMISSIONS["tenant_admin"]
    assert "tenant.create" not in perms
    assert "tenant.manage" not in perms
    assert "tenant.read" not in perms
    assert "org.create" in perms
    assert "org.manage" in perms
    assert "organization.access" in perms
    assert "settings.manage" in perms
    assert "auth.read" in perms
    assert "auth.manage" in perms


def test_org_admin_has_org_permissions():
    perms = DEFAULT_ROLE_PERMISSIONS["org_admin"]
    assert "org.manage" in perms
    assert "employee.read" in perms
    assert "employee.manage" in perms
    assert "organization.access" in perms
    assert "settings.manage" in perms
    assert "auth.read" in perms
    assert "auth.manage" in perms


def test_tenant_admin_does_not_have_platform_admin():
    perms = DEFAULT_ROLE_PERMISSIONS["tenant_admin"]
    assert "platform.admin" not in perms


def test_org_admin_does_not_have_platform_admin():
    perms = DEFAULT_ROLE_PERMISSIONS["org_admin"]
    assert "platform.admin" not in perms


def test_org_admin_does_not_have_tenant_create():
    perms = DEFAULT_ROLE_PERMISSIONS["org_admin"]
    assert "tenant.create" not in perms
    assert "tenant.manage" not in perms
    assert "tenant.read" not in perms


def test_all_tenant_admin_permissions_are_registered():
    for code in DEFAULT_ROLE_PERMISSIONS["tenant_admin"]:
        assert code in DEFAULT_PERMISSIONS, f"tenant_admin permission '{code}' is not in DEFAULT_PERMISSIONS"


def test_all_org_admin_permissions_are_registered():
    for code in DEFAULT_ROLE_PERMISSIONS["org_admin"]:
        assert code in DEFAULT_PERMISSIONS, f"org_admin permission '{code}' is not in DEFAULT_PERMISSIONS"


def test_org_viewer_role_is_defined_in_policy():
    assert "org_viewer" in DEFAULT_ROLE_PERMISSIONS


def test_org_member_role_is_defined_in_policy():
    assert "org_member" in DEFAULT_ROLE_PERMISSIONS


def test_org_viewer_has_read_only_organization_permissions():
    perms = DEFAULT_ROLE_PERMISSIONS["org_viewer"]
    assert "organization.access" in perms
    assert "project.read" in perms
    assert "org.manage" not in perms
    assert "auth.manage" not in perms
    assert "settings.manage" not in perms
    assert "employee.manage" not in perms


def test_org_member_has_org_viewer_permissions_plus_collaboration():
    viewer_perms = DEFAULT_ROLE_PERMISSIONS["org_viewer"]
    member_perms = DEFAULT_ROLE_PERMISSIONS["org_member"]
    assert viewer_perms <= member_perms
    assert "collaboration.manage" in member_perms
    assert "timesheet.submit" in member_perms
    assert "org.manage" not in member_perms
    assert "auth.manage" not in member_perms


def test_all_org_viewer_and_org_member_permissions_are_registered():
    for role_name in ("org_viewer", "org_member"):
        for code in DEFAULT_ROLE_PERMISSIONS[role_name]:
            assert code in DEFAULT_PERMISSIONS, (
                f"{role_name} permission '{code}' is not in DEFAULT_PERMISSIONS"
            )


def test_new_permissions_are_registered():
    for code in ("tenant.create", "tenant.manage", "tenant.read", "org.create", "org.manage"):
        assert code in DEFAULT_PERMISSIONS, f"'{code}' is missing from DEFAULT_PERMISSIONS"


# ---------------------------------------------------------------------------
# 7. Bootstrap: roles seeded in DB
# ---------------------------------------------------------------------------

def test_tenant_admin_role_is_seeded_in_db(services):
    """After bootstrap, a tenant_admin role exists in the DB."""
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name("tenant_admin")
    assert role is not None, "tenant_admin role was not seeded"


def test_org_admin_role_is_seeded_in_db(services):
    """After bootstrap, an org_admin role exists in the DB."""
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name("org_admin")
    assert role is not None, "org_admin role was not seeded"


def test_org_viewer_role_is_seeded_in_db(services):
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name("org_viewer")
    assert role is not None, "org_viewer role was not seeded"
    assert role.allowed_scope_type == "organization"


def test_org_member_role_is_seeded_in_db(services):
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name("org_member")
    assert role is not None, "org_member role was not seeded"
    assert role.allowed_scope_type == "organization"


def test_tenant_admin_role_has_seeded_permissions(services):
    """The seeded tenant_admin role has its expected permissions wired."""
    auth = services["auth_service"]

    tenant_id, _ = _active_context_ids(services)
    user = auth.register_user(
        "p2a-tadmin-perms",
        "StrongPass123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    principal = auth.build_principal(user)

    assert "tenant.create" not in principal.permissions
    assert "tenant.manage" not in principal.permissions
    assert "tenant.read" not in principal.permissions
    assert "org.create" in principal.permissions
    assert "org.manage" in principal.permissions
    assert "auth.manage" in principal.permissions


def test_org_admin_role_has_seeded_permissions(services):
    """The seeded org_admin role has its expected permissions wired."""
    auth = services["auth_service"]

    tenant_id, organization_id = _active_context_ids(services)
    user = auth.register_user(
        "p2a-oadmin-perms",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_org_admin(services, user.id, organization_id)
    principal = auth.build_principal(user)

    assert "org.manage" in principal.permissions
    assert "employee.read" in principal.permissions
    assert "employee.manage" in principal.permissions
    assert "organization.access" in principal.permissions
    assert "settings.manage" in principal.permissions


# ---------------------------------------------------------------------------
# 8–9. Permission assignment via build_principal
# ---------------------------------------------------------------------------

def test_user_assigned_tenant_admin_gets_correct_permissions(services):
    auth = services["auth_service"]
    tenant_id, _ = _active_context_ids(services)

    user = auth.register_user(
        "p2a-assign-tadmin",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    auth.assign_role(user.id, "tenant_admin")

    principal = auth.build_principal(user)
    assert "tenant_admin" in principal.role_names
    assert "tenant.create" not in principal.permissions
    assert "tenant.manage" not in principal.permissions
    assert "platform.admin" not in principal.permissions


def test_user_assigned_org_admin_gets_correct_permissions(services):
    auth = services["auth_service"]
    tenant_id, organization_id = _active_context_ids(services)

    user = auth.register_user(
        "p2a-assign-oadmin",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_org_admin(services, user.id, organization_id)

    principal = auth.build_principal(user)
    assert "org_admin" in principal.role_names
    assert "org.manage" in principal.permissions
    assert "employee.manage" in principal.permissions
    assert "tenant.create" not in principal.permissions
    assert "platform.admin" not in principal.permissions


def test_user_assigned_org_viewer_gets_correct_permissions(services):
    auth = services["auth_service"]
    tenant_id, organization_id = _active_context_ids(services)

    user = auth.register_user(
        "p2a-assign-oviewer",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_org_role(services, user.id, organization_id, "org_viewer")

    principal = auth.build_principal(user)
    assert "org_viewer" in principal.role_names
    assert "organization.access" in principal.permissions
    assert "project.read" in principal.permissions
    assert "org.manage" not in principal.permissions
    assert "auth.manage" not in principal.permissions


def test_user_assigned_org_member_gets_correct_permissions(services):
    auth = services["auth_service"]
    tenant_id, organization_id = _active_context_ids(services)

    user = auth.register_user(
        "p2a-assign-omember",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_org_role(services, user.id, organization_id, "org_member")

    principal = auth.build_principal(user)
    assert "org_member" in principal.role_names
    assert "collaboration.manage" in principal.permissions
    assert "timesheet.submit" in principal.permissions
    assert "org.manage" not in principal.permissions


def test_org_admin_is_effective_only_in_its_canonical_organization(services):
    from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
        SqlAlchemyOrganizationRepository,
    )
    from src.core.platform.domain.master_data.org.organization import Organization

    auth = services["auth_service"]
    session = services["session"]
    tenant_id, organization_id = _active_context_ids(services)
    other = Organization.create(
        "ORG-SCOPE-OTHER",
        "Other Scope Organization",
        tenant_id=tenant_id,
        is_active=True,
    )
    SqlAlchemyOrganizationRepository(session).add(other)
    session.flush()
    user = auth.register_user(
        "p2a-oadmin-context",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_org_admin(services, user.id, organization_id)

    active = auth.build_principal_for_context(
        user,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )
    other_context = auth.build_principal_for_context(
        user,
        tenant_id=tenant_id,
        organization_id=other.id,
    )

    assert "org_admin" in active.role_names
    assert "org.manage" in active.permissions
    assert "org_admin" not in other_context.role_names
    assert "org.manage" not in other_context.permissions
    assert organization_id in other_context.scoped_access["organization"]


# ---------------------------------------------------------------------------
# 10. is_platform_admin() end-to-end
# ---------------------------------------------------------------------------


def test_is_platform_admin_returns_true_for_admin(services):
    """The bootstrapped admin user has platform.admin and is_platform_admin() returns True."""
    auth = services["auth_service"]
    user_session = services["user_session"]

    admin = auth.authenticate("admin", "ChangeMe123!")
    principal = auth.build_principal(admin)
    assert "platform.admin" in principal.permissions

    user_session.set_principal(principal)
    assert user_session.is_platform_admin() is True


def test_is_platform_admin_returns_false_for_tenant_admin(services):
    auth = services["auth_service"]
    user_session = services["user_session"]

    user = auth.register_user("p2a-padmin-tadmin", "StrongPass123!", role_names=["tenant_admin"])
    principal = auth.build_principal(user)

    user_session.set_principal(principal)
    assert user_session.is_platform_admin() is False


def test_is_platform_admin_returns_false_for_org_admin(services):
    auth = services["auth_service"]
    user_session = services["user_session"]

    _, organization_id = _active_context_ids(services)
    user = auth.register_user(
        "p2a-padmin-oadmin",
        "StrongPass123!",
        role_names=["viewer"],
    )
    _bind_org_admin(services, user.id, organization_id)
    principal = auth.build_principal(user)

    user_session.set_principal(principal)
    assert user_session.is_platform_admin() is False


# ---------------------------------------------------------------------------
# 11. Org-scoped binding: same role can be assigned for multiple organizations
# ---------------------------------------------------------------------------

def test_org_admin_binding_supports_organization_scope(services):
    """Canonical bindings support the same role in multiple organizations."""
    from sqlalchemy import select

    from src.core.platform.infrastructure.persistence.orm.security.auth.auth import RoleBindingORM
    from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import SqlAlchemyOrganizationRepository
    from src.core.platform.domain.master_data.org.organization import Organization

    session = services["session"]
    auth = services["auth_service"]
    tenant_context = services["tenant_context_service"]
    active_tenant_id = tenant_context.get_active_tenant_id()

    org_repo = SqlAlchemyOrganizationRepository(session)
    org_a = Organization.create("SCOPE-A", "Scope Org A", tenant_id=active_tenant_id, is_active=True)
    org_b = Organization.create("SCOPE-B", "Scope Org B", tenant_id=active_tenant_id, is_active=False)
    org_repo.add(org_a)
    org_repo.add(org_b)
    session.flush()

    user = auth.register_user("p2a-orgscope", "StrongPass123!", role_names=["viewer"])
    org_admin_role = auth._role_repo.get_by_name("org_admin")
    assert org_admin_role is not None

    binding_org_a = RoleBinding.create(
        principal_id=user.id,
        role_id=org_admin_role.id,
        tenant_id=active_tenant_id,
        actual_scope_type="organization",
        actual_scope_id=org_a.id,
    )
    binding_org_b = RoleBinding.create(
        principal_id=user.id,
        role_id=org_admin_role.id,
        tenant_id=active_tenant_id,
        actual_scope_type="organization",
        actual_scope_id=org_b.id,
    )

    auth._role_binding_repo.add(binding_org_a)
    session.flush()
    auth._role_binding_repo.add(binding_org_b)
    session.flush()

    rows = session.execute(
        select(RoleBindingORM).where(
            RoleBindingORM.principal_id == user.id,
            RoleBindingORM.role_id == org_admin_role.id,
        )
    ).scalars().all()

    org_ids = {r.actual_scope_id for r in rows}
    assert org_a.id in org_ids
    assert org_b.id in org_ids
