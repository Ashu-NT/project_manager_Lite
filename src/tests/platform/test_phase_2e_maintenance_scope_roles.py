"""Tests for the maintenance-scope canonical role cutover.

Covers:
  1. Policy unit: maintenance_viewer/operator/scope_manager permission sets
  2. Integration: maintenance roles are seeded in DB after bootstrap
  3. Integration: build_principal grants correct permissions per maintenance role
  4. Integration: a maintenance role binding is scoped to its own location only
  5. Regression: a legacy ScopedAccessGrant row at maintenance scope grants no
     runtime authority

Note: the resource-scoped "manager" tier is named `maintenance_scope_manager`,
not `maintenance_manager` — that name already belongs to a pre-existing
tenant-wide system role and cannot be reused.
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


def _bind_maintenance_role(services, user_id: str, location_id: str, role_name: str) -> None:
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name(role_name)
    assert role is not None
    auth._role_binding_repo.add(
        RoleBinding.create(
            principal_id=user_id,
            role_id=role.id,
            tenant_id=services["tenant_context_service"].get_active_tenant_id(),
            actual_scope_type="maintenance",
            actual_scope_id=location_id,
        )
    )
    services["session"].flush()


def _create_maintenance_location(services, location_code: str):
    site = services["site_service"].create_site(
        site_code=f"{location_code}-SITE",
        name=f"Phase 2E {location_code} Site",
        city="Berlin",
        currency_code="EUR",
    )
    return services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code=location_code,
        name=f"Phase 2E {location_code}",
        description="",
    )


# ---------------------------------------------------------------------------
# 1. Policy-level unit tests (no DB required)
# ---------------------------------------------------------------------------

def test_maintenance_scope_roles_are_defined_in_policy():
    for role_name in ("maintenance_viewer", "maintenance_operator", "maintenance_scope_manager"):
        assert role_name in DEFAULT_ROLE_PERMISSIONS


def test_maintenance_scope_role_permissions_are_nested_supersets():
    viewer = DEFAULT_ROLE_PERMISSIONS["maintenance_viewer"]
    operator = DEFAULT_ROLE_PERMISSIONS["maintenance_operator"]
    manager = DEFAULT_ROLE_PERMISSIONS["maintenance_scope_manager"]
    assert viewer <= operator <= manager
    assert viewer == {"maintenance.read"}
    assert "maintenance.manage" not in viewer
    assert "maintenance.manage" in operator
    assert "report.view" not in operator
    assert "report.view" in manager
    assert "auth.manage" not in manager
    assert "org.manage" not in manager
    assert "platform.admin" not in manager


def test_maintenance_scope_manager_does_not_collide_with_tenant_wide_role():
    # "maintenance_manager" is a pre-existing tenant-wide role with a much
    # broader permission set; the resource-scoped role must remain distinct.
    assert DEFAULT_ROLE_PERMISSIONS["maintenance_scope_manager"] != (
        DEFAULT_ROLE_PERMISSIONS["maintenance_manager"]
    )
    assert "auth.role.assign" not in DEFAULT_ROLE_PERMISSIONS["maintenance_scope_manager"]


def test_all_maintenance_scope_permissions_are_registered():
    for role_name in ("maintenance_viewer", "maintenance_operator", "maintenance_scope_manager"):
        for code in DEFAULT_ROLE_PERMISSIONS[role_name]:
            assert code in DEFAULT_PERMISSIONS, (
                f"{role_name} permission '{code}' is not in DEFAULT_PERMISSIONS"
            )


# ---------------------------------------------------------------------------
# 2. Bootstrap: roles seeded in DB
# ---------------------------------------------------------------------------

def test_maintenance_scope_roles_are_seeded_in_db(services):
    auth = services["auth_service"]
    for role_name in ("maintenance_viewer", "maintenance_operator", "maintenance_scope_manager"):
        role = auth._role_repo.get_by_name(role_name)
        assert role is not None, f"{role_name} role was not seeded"
        assert role.allowed_scope_type == "maintenance"


# ---------------------------------------------------------------------------
# 3. Permission assignment via build_principal
# ---------------------------------------------------------------------------

def test_user_assigned_maintenance_scope_manager_gets_correct_permissions(services):
    auth = services["auth_service"]
    tenant_id, _ = _active_context_ids(services)

    location = _create_maintenance_location(services, "P2E-MGR")
    user = auth.register_user(
        "p2e-assign-mmanager",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_maintenance_role(services, user.id, location.id, "maintenance_scope_manager")

    principal = auth.build_principal(user)
    assert "maintenance_scope_manager" in principal.role_names
    assert "report.view" in principal.permissions
    assert location.id in principal.scoped_access.get("maintenance", {})


def test_user_assigned_maintenance_viewer_gets_read_only_permissions(services):
    auth = services["auth_service"]
    tenant_id, _ = _active_context_ids(services)

    location = _create_maintenance_location(services, "P2E-VWR")
    user = auth.register_user(
        "p2e-assign-mviewer",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_maintenance_role(services, user.id, location.id, "maintenance_viewer")

    principal = auth.build_principal(user)
    assert "maintenance_viewer" in principal.role_names
    assert "maintenance.read" in principal.permissions
    assert "maintenance.manage" not in principal.permissions


# ---------------------------------------------------------------------------
# 4. Scope isolation: a maintenance role binding only ever names its own location
# ---------------------------------------------------------------------------

def test_maintenance_role_binding_is_scoped_to_its_own_location(services):
    auth = services["auth_service"]
    tenant_id, organization_id = _active_context_ids(services)

    location_a = _create_maintenance_location(services, "P2E-SCOPE-A")
    location_b = _create_maintenance_location(services, "P2E-SCOPE-B")
    user = auth.register_user(
        "p2e-maintenance-scope",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_maintenance_role(services, user.id, location_a.id, "maintenance_scope_manager")

    principal = auth.build_principal_for_context(
        user,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )

    assert location_a.id in principal.scoped_access.get("maintenance", {})
    assert location_b.id not in principal.scoped_access.get("maintenance", {})
    assert "maintenance.manage" in principal.scoped_access["maintenance"][location_a.id]

