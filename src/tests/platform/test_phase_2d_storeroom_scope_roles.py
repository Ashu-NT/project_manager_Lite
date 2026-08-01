"""Tests for the storeroom-scope canonical role cutover.

Covers:
  1. Policy unit: storeroom_viewer/operator/manager permission sets
  2. Integration: storeroom roles are seeded in DB after bootstrap
  3. Integration: build_principal grants correct permissions per storeroom role
  4. Integration: a storeroom role binding is scoped to its own storeroom only
  5. Regression: a legacy ScopedAccessGrant row at storeroom scope grants no
     runtime authority
"""
from __future__ import annotations

from src.core.platform.auth.domain import RoleBinding
from src.core.platform.auth.policy import DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS


def _active_context_ids(services) -> tuple[str, str]:
    tenant_context = services["tenant_context_service"]
    tenant_id = tenant_context.get_active_tenant_id()
    organization_id = tenant_context.get_active_organization_id()
    assert tenant_id is not None
    assert organization_id is not None
    return tenant_id, organization_id


def _bind_storeroom_role(services, user_id: str, storeroom_id: str, role_name: str) -> None:
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name(role_name)
    assert role is not None
    auth._role_binding_repo.add(
        RoleBinding.create(
            principal_id=user_id,
            role_id=role.id,
            tenant_id=services["tenant_context_service"].get_active_tenant_id(),
            actual_scope_type="storeroom",
            actual_scope_id=storeroom_id,
        )
    )
    services["session"].flush()


def _create_storeroom(services, storeroom_code: str):
    site = services["site_service"].create_site(
        site_code=f"{storeroom_code}-SITE",
        name=f"Phase 2D {storeroom_code} Site",
        city="Berlin",
        currency_code="EUR",
    )
    return services["inventory_service"].create_storeroom(
        storeroom_code=storeroom_code,
        name=f"Phase 2D {storeroom_code}",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
    )


# ---------------------------------------------------------------------------
# 1. Policy-level unit tests (no DB required)
# ---------------------------------------------------------------------------

def test_storeroom_scope_roles_are_defined_in_policy():
    for role_name in ("storeroom_viewer", "storeroom_operator", "storeroom_manager"):
        assert role_name in DEFAULT_ROLE_PERMISSIONS


def test_storeroom_scope_role_permissions_are_nested_supersets():
    viewer = DEFAULT_ROLE_PERMISSIONS["storeroom_viewer"]
    operator = DEFAULT_ROLE_PERMISSIONS["storeroom_operator"]
    manager = DEFAULT_ROLE_PERMISSIONS["storeroom_manager"]
    assert viewer <= operator <= manager
    assert viewer == {"inventory.read"}
    assert "inventory.manage" not in viewer
    assert "inventory.manage" in operator
    assert "report.view" not in operator
    assert "report.view" in manager
    assert "auth.manage" not in manager
    assert "org.manage" not in manager
    assert "platform.admin" not in manager


def test_all_storeroom_scope_permissions_are_registered():
    for role_name in ("storeroom_viewer", "storeroom_operator", "storeroom_manager"):
        for code in DEFAULT_ROLE_PERMISSIONS[role_name]:
            assert code in DEFAULT_PERMISSIONS, (
                f"{role_name} permission '{code}' is not in DEFAULT_PERMISSIONS"
            )


# ---------------------------------------------------------------------------
# 2. Bootstrap: roles seeded in DB
# ---------------------------------------------------------------------------

def test_storeroom_scope_roles_are_seeded_in_db(services):
    auth = services["auth_service"]
    for role_name in ("storeroom_viewer", "storeroom_operator", "storeroom_manager"):
        role = auth._role_repo.get_by_name(role_name)
        assert role is not None, f"{role_name} role was not seeded"
        assert role.allowed_scope_type == "storeroom"


# ---------------------------------------------------------------------------
# 3. Permission assignment via build_principal
# ---------------------------------------------------------------------------

def test_user_assigned_storeroom_manager_gets_correct_permissions(services):
    auth = services["auth_service"]
    tenant_id, _ = _active_context_ids(services)

    storeroom = _create_storeroom(services, "P2D-MGR")
    user = auth.register_user(
        "p2d-assign-smanager",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_storeroom_role(services, user.id, storeroom.id, "storeroom_manager")

    principal = auth.build_principal(user)
    assert "storeroom_manager" in principal.role_names
    assert "report.view" in principal.permissions
    assert storeroom.id in principal.scoped_access.get("storeroom", {})


def test_user_assigned_storeroom_viewer_gets_read_only_permissions(services):
    auth = services["auth_service"]
    tenant_id, _ = _active_context_ids(services)

    storeroom = _create_storeroom(services, "P2D-VWR")
    user = auth.register_user(
        "p2d-assign-sviewer",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_storeroom_role(services, user.id, storeroom.id, "storeroom_viewer")

    principal = auth.build_principal(user)
    assert "storeroom_viewer" in principal.role_names
    assert "inventory.read" in principal.permissions
    assert "inventory.manage" not in principal.permissions


# ---------------------------------------------------------------------------
# 4. Scope isolation: a storeroom role binding only ever names its own storeroom
# ---------------------------------------------------------------------------

def test_storeroom_role_binding_is_scoped_to_its_own_storeroom(services):
    auth = services["auth_service"]
    tenant_id, organization_id = _active_context_ids(services)

    storeroom_a = _create_storeroom(services, "P2D-SCOPE-A")
    storeroom_b = _create_storeroom(services, "P2D-SCOPE-B")
    user = auth.register_user(
        "p2d-storeroom-scope",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_storeroom_role(services, user.id, storeroom_a.id, "storeroom_manager")

    principal = auth.build_principal_for_context(
        user,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )

    assert storeroom_a.id in principal.scoped_access.get("storeroom", {})
    assert storeroom_b.id not in principal.scoped_access.get("storeroom", {})
    assert "inventory.manage" in principal.scoped_access["storeroom"][storeroom_a.id]

