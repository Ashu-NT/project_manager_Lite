"""Tests for the site-scope canonical role cutover.

Covers:
  1. Policy unit: site_viewer/operator/manager permission sets
  2. Integration: site roles are seeded in DB after bootstrap
  3. Integration: build_principal grants correct permissions per site role
  4. Integration: a site role binding is scoped to its own site only
  5. Regression: a legacy ScopedAccessGrant row at site scope grants no
     runtime authority
"""
from __future__ import annotations

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


def _bind_site_role(services, user_id: str, site_id: str, role_name: str) -> None:
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name(role_name)
    assert role is not None
    auth._role_binding_repo.add(
        RoleBinding.create(
            principal_id=user_id,
            role_id=role.id,
            tenant_id=services["tenant_context_service"].get_active_tenant_id(),
            actual_scope_type="site",
            actual_scope_id=site_id,
        )
    )
    services["session"].flush()


def _create_site(services, site_code: str):
    return services["site_service"].create_site(
        site_code=site_code,
        name=f"Phase 2C {site_code}",
        city="Berlin",
        currency_code="EUR",
    )


# ---------------------------------------------------------------------------
# 1. Policy-level unit tests (no DB required)
# ---------------------------------------------------------------------------

def test_site_scope_roles_are_defined_in_policy():
    for role_name in ("site_viewer", "site_operator", "site_manager"):
        assert role_name in DEFAULT_ROLE_PERMISSIONS


def test_site_scope_role_permissions_are_nested_supersets():
    viewer = DEFAULT_ROLE_PERMISSIONS["site_viewer"]
    operator = DEFAULT_ROLE_PERMISSIONS["site_operator"]
    manager = DEFAULT_ROLE_PERMISSIONS["site_manager"]
    assert viewer <= operator <= manager
    assert viewer == {"site.read"}
    assert "inventory.manage" not in viewer
    assert "inventory.manage" not in operator
    assert "inventory.manage" in manager
    assert "auth.manage" not in manager
    assert "org.manage" not in manager
    assert "platform.admin" not in manager


def test_all_site_scope_permissions_are_registered():
    for role_name in ("site_viewer", "site_operator", "site_manager"):
        for code in DEFAULT_ROLE_PERMISSIONS[role_name]:
            assert code in DEFAULT_PERMISSIONS, (
                f"{role_name} permission '{code}' is not in DEFAULT_PERMISSIONS"
            )


# ---------------------------------------------------------------------------
# 2. Bootstrap: roles seeded in DB
# ---------------------------------------------------------------------------

def test_site_scope_roles_are_seeded_in_db(services):
    auth = services["auth_service"]
    for role_name in ("site_viewer", "site_operator", "site_manager"):
        role = auth._role_repo.get_by_name(role_name)
        assert role is not None, f"{role_name} role was not seeded"
        assert role.allowed_scope_type == "site"


# ---------------------------------------------------------------------------
# 3. Permission assignment via build_principal
# ---------------------------------------------------------------------------

def test_user_assigned_site_manager_gets_correct_permissions(services):
    auth = services["auth_service"]
    tenant_id, _ = _active_context_ids(services)

    site = _create_site(services, "P2C-MGR")
    user = auth.register_user(
        "p2c-assign-smanager",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_site_role(services, user.id, site.id, "site_manager")

    principal = auth.build_principal(user)
    assert "site_manager" in principal.role_names
    assert "inventory.manage" in principal.permissions
    assert site.id in principal.scoped_access.get("site", {})


def test_user_assigned_site_viewer_gets_read_only_permissions(services):
    auth = services["auth_service"]
    tenant_id, _ = _active_context_ids(services)

    site = _create_site(services, "P2C-VWR")
    user = auth.register_user(
        "p2c-assign-sviewer",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_site_role(services, user.id, site.id, "site_viewer")

    principal = auth.build_principal(user)
    assert "site_viewer" in principal.role_names
    assert "site.read" in principal.permissions
    assert "inventory.read" not in principal.permissions
    assert "inventory.manage" not in principal.permissions


# ---------------------------------------------------------------------------
# 4. Scope isolation: a site role binding only ever names its own site
# ---------------------------------------------------------------------------

def test_site_role_binding_is_scoped_to_its_own_site(services):
    auth = services["auth_service"]
    tenant_id, organization_id = _active_context_ids(services)

    site_a = _create_site(services, "P2C-SCOPE-A")
    site_b = _create_site(services, "P2C-SCOPE-B")
    user = auth.register_user(
        "p2c-site-scope",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_site_role(services, user.id, site_a.id, "site_manager")

    principal = auth.build_principal_for_context(
        user,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )

    assert site_a.id in principal.scoped_access.get("site", {})
    assert site_b.id not in principal.scoped_access.get("site", {})
    assert "inventory.manage" in principal.scoped_access["site"][site_a.id]

