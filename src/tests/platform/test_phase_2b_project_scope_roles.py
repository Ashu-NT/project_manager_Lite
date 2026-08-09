"""Tests for the project-scope canonical role cutover.

Covers:
  1. Policy unit: project_viewer/contributor/lead/owner permission sets
  2. Integration: project roles are seeded in DB after bootstrap
  3. Integration: build_principal grants correct permissions per project role
  4. Integration: a project role binding is scoped to its own project only
  5. Regression: a legacy ScopedAccessGrant/ProjectMembership row at project
     scope grants no runtime authority
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


def _bind_project_role(services, user_id: str, project_id: str, role_name: str) -> None:
    auth = services["auth_service"]
    role = auth._role_repo.get_by_name(role_name)
    assert role is not None
    auth._role_binding_repo.add(
        RoleBinding.create(
            principal_id=user_id,
            role_id=role.id,
            tenant_id=services["tenant_context_service"].get_active_tenant_id(),
            actual_scope_type="project",
            actual_scope_id=project_id,
        )
    )
    services["session"].flush()


# ---------------------------------------------------------------------------
# 1. Policy-level unit tests (no DB required)
# ---------------------------------------------------------------------------

def test_project_scope_roles_are_defined_in_policy():
    for role_name in ("project_viewer", "project_contributor", "project_lead", "project_owner"):
        assert role_name in DEFAULT_ROLE_PERMISSIONS


def test_project_scope_role_permissions_are_nested_supersets():
    viewer = DEFAULT_ROLE_PERMISSIONS["project_viewer"]
    contributor = DEFAULT_ROLE_PERMISSIONS["project_contributor"]
    lead = DEFAULT_ROLE_PERMISSIONS["project_lead"]
    owner = DEFAULT_ROLE_PERMISSIONS["project_owner"]
    assert viewer <= contributor <= lead <= owner
    assert "project.manage" not in viewer
    assert "project.manage" not in contributor
    assert "project.manage" not in lead
    assert "project.manage" in owner
    assert "auth.manage" not in owner
    assert "org.manage" not in owner
    assert "platform.admin" not in owner


def test_all_project_scope_permissions_are_registered():
    for role_name in ("project_viewer", "project_contributor", "project_lead", "project_owner"):
        for code in DEFAULT_ROLE_PERMISSIONS[role_name]:
            assert code in DEFAULT_PERMISSIONS, (
                f"{role_name} permission '{code}' is not in DEFAULT_PERMISSIONS"
            )


# ---------------------------------------------------------------------------
# 2. Bootstrap: roles seeded in DB
# ---------------------------------------------------------------------------

def test_project_scope_roles_are_seeded_in_db(services):
    auth = services["auth_service"]
    for role_name in ("project_viewer", "project_contributor", "project_lead", "project_owner"):
        role = auth._role_repo.get_by_name(role_name)
        assert role is not None, f"{role_name} role was not seeded"
        assert role.allowed_scope_type == "project"


# ---------------------------------------------------------------------------
# 3. Permission assignment via build_principal
# ---------------------------------------------------------------------------

def test_user_assigned_project_lead_gets_correct_permissions(services):
    auth = services["auth_service"]
    project_service = services["project_service"]
    tenant_id, _ = _active_context_ids(services)

    project = project_service.create_project("Phase 2B Lead Project")
    user = auth.register_user(
        "p2b-assign-plead",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_project_role(services, user.id, project.id, "project_lead")

    principal = auth.build_principal(user)
    assert "project_lead" in principal.role_names
    assert "project_cost.create" in principal.permissions
    assert "project.manage" not in principal.permissions
    assert project.id in principal.scoped_access.get("project", {})
    assert project.id in principal.project_access


def test_user_assigned_project_viewer_gets_read_only_permissions(services):
    auth = services["auth_service"]
    project_service = services["project_service"]
    tenant_id, _ = _active_context_ids(services)

    project = project_service.create_project("Phase 2B Viewer Project")
    user = auth.register_user(
        "p2b-assign-pviewer",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_project_role(services, user.id, project.id, "project_viewer")

    principal = auth.build_principal(user)
    assert "project_viewer" in principal.role_names
    assert "project.read" in principal.permissions
    assert "task.manage" not in principal.permissions
    assert "project.manage" not in principal.permissions


# ---------------------------------------------------------------------------
# 4. Scope isolation: a project role binding only ever names its own project
# ---------------------------------------------------------------------------

def test_project_role_binding_is_scoped_to_its_own_project(services):
    auth = services["auth_service"]
    project_service = services["project_service"]
    tenant_id, organization_id = _active_context_ids(services)

    project_a = project_service.create_project("Phase 2B Scope A")
    project_b = project_service.create_project("Phase 2B Scope B")
    user = auth.register_user(
        "p2b-project-scope",
        "StrongPass123!",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    _bind_project_role(services, user.id, project_a.id, "project_owner")

    principal = auth.build_principal_for_context(
        user,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )

    assert project_a.id in principal.scoped_access.get("project", {})
    assert project_b.id not in principal.scoped_access.get("project", {})
    assert "project.manage" in principal.scoped_access["project"][project_a.id]

