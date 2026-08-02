from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.core.platform.auth.application import CanonicalRoleResolver
from src.core.platform.auth.domain import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    Role,
    RoleBinding,
    RolePermissionBinding,
)
from src.core.platform.common.exceptions import BusinessRuleError


def _resolver(services, *, owned_scopes=None) -> CanonicalRoleResolver:
    repositories = _role_repositories(services)
    owned = dict(owned_scopes or {})
    return CanonicalRoleResolver(
        role_binding_repo=repositories.role_binding_repo,
        role_repo=repositories.role_repo,
        role_permission_repo=repositories.role_permission_repo,
        permission_repo=repositories.permission_repo,
        scope_tenant_resolvers={
            scope_type: (
                lambda tenant_id, scope_id, expected=expected: (
                    (tenant_id, scope_id) in expected
                )
            )
            for scope_type, expected in owned.items()
        },
    )


def _role_repositories(services):
    auth = services["auth_service"]
    return SimpleNamespace(
        role_binding_repo=(
            services["role_governance_service"]._role_binding_repo
        ),
        role_repo=auth._role_repo,
        role_permission_repo=auth._role_permission_repo,
        permission_repo=auth._permission_repo,
    )


def _create_user_without_legacy_roles(services, username: str):
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    assert tenant_id is not None
    user = services["auth_service"].register_user(
        username,
        "CanonicalResolver123!",
        role_names=[],
        tenant_id=tenant_id,
    )
    return user, tenant_id


def _add_role_permission(services, role: Role, permission_code: str) -> None:
    repositories = _role_repositories(services)
    permission = repositories.permission_repo.get_by_code(permission_code)
    assert permission is not None
    repositories.role_permission_repo.add(
        RolePermissionBinding.create(
            role_id=role.id,
            permission_id=permission.id,
        )
    )


def test_resolves_platform_authority_without_customer_context(services) -> None:
    repositories = _role_repositories(services)
    user = services["auth_service"].register_user(
        "canonical-resolver-platform",
        "CanonicalResolver123!",
        role_names=[],
    )
    admin = repositories.role_repo.get_by_name("admin")
    assert admin is not None
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=admin.id,
            actual_scope_type=ROLE_SCOPE_PLATFORM,
        )
    )
    services["session"].commit()

    authority = _resolver(services).resolve(
        user.id,
        tenant_id=None,
        organization_id=None,
    )

    assert authority.role_names == {"admin"}
    assert "platform.admin" in authority.unrestricted_permissions
    assert authority.scoped_access == {}


def test_platform_authority_cannot_enter_customer_context(services) -> None:
    repositories = _role_repositories(services)
    user, tenant_id = _create_user_without_legacy_roles(
        services,
        "canonical-resolver-platform-customer-denial",
    )
    admin = repositories.role_repo.get_by_name("admin")
    assert admin is not None
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=admin.id,
            actual_scope_type=ROLE_SCOPE_PLATFORM,
        )
    )
    services["session"].commit()

    with pytest.raises(BusinessRuleError) as exc_info:
        _resolver(services).resolve(
            user.id,
            tenant_id=tenant_id,
            organization_id=None,
        )

    assert exc_info.value.code == "PLATFORM_CUSTOMER_CONTEXT_DENIED"


def test_resolves_tenant_and_resource_authority(services) -> None:
    repositories = _role_repositories(services)
    user, tenant_id = _create_user_without_legacy_roles(
        services,
        "canonical-resolver-scopes",
    )
    viewer = repositories.role_repo.get_by_name("viewer")
    assert viewer is not None
    project_role = Role.create(
        name="project_task_editor",
        display_name="Project Task Editor",
        is_system=False,
        tenant_id=tenant_id,
        allowed_scope_type="project",
    )
    repositories.role_repo.add(project_role)
    services["session"].flush()
    _add_role_permission(services, project_role, "task.manage")
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=viewer.id,
            tenant_id=tenant_id,
            actual_scope_type=ROLE_SCOPE_TENANT,
        )
    )
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=project_role.id,
            tenant_id=tenant_id,
            actual_scope_type="project",
            actual_scope_id="project-1",
        )
    )
    services["session"].commit()

    authority = _resolver(
        services,
        owned_scopes={"project": {(tenant_id, "project-1")}},
    ).resolve(user.id, tenant_id=tenant_id, organization_id=None)

    assert authority.role_names == {
        "viewer",
        "project_task_editor",
    }
    assert "project.read" in authority.unrestricted_permissions
    assert "task.manage" in authority.permissions
    assert "task.manage" not in authority.unrestricted_permissions
    assert authority.scoped_access == {
        "project": {"project-1": frozenset({"task.manage"})}
    }

    tenant_authority = _resolver(services).resolve_tenant_authority(
        user.id,
        tenant_id=tenant_id,
    )
    assert tenant_authority.role_names == {"viewer"}
    assert "project.read" in tenant_authority.permissions
    assert "task.manage" not in tenant_authority.permissions
    assert tenant_authority.scoped_access == {}


def test_organization_role_is_effective_only_in_active_organization(services) -> None:
    repositories = _role_repositories(services)
    user, tenant_id = _create_user_without_legacy_roles(
        services,
        "canonical-resolver-organization",
    )
    org_admin = repositories.role_repo.get_by_name("org_admin")
    assert org_admin is not None
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=org_admin.id,
            tenant_id=tenant_id,
            actual_scope_type="organization",
            actual_scope_id="organization-1",
        )
    )
    services["session"].commit()
    resolver = _resolver(
        services,
        owned_scopes={
            "organization": {(tenant_id, "organization-1")},
        },
    )

    inactive = resolver.resolve(
        user.id,
        tenant_id=tenant_id,
        organization_id="organization-2",
    )
    active = resolver.resolve(
        user.id,
        tenant_id=tenant_id,
        organization_id="organization-1",
    )

    assert "org_admin" not in inactive.role_names
    assert "org.manage" not in inactive.permissions
    assert "organization-1" in inactive.scoped_access["organization"]
    assert "org_admin" in active.role_names
    assert "org.manage" in active.unrestricted_permissions


def test_expired_and_revoked_bindings_do_not_grant_authority(services) -> None:
    repositories = _role_repositories(services)
    user, tenant_id = _create_user_without_legacy_roles(
        services,
        "canonical-resolver-inactive-bindings",
    )
    viewer = repositories.role_repo.get_by_name("viewer")
    planner = repositories.role_repo.get_by_name("planner")
    assert viewer is not None
    assert planner is not None
    now = datetime.now(timezone.utc)
    repositories.role_binding_repo.add(
        RoleBinding(
            id="expired-canonical-binding",
            principal_type="user",
            principal_id=user.id,
            role_id=viewer.id,
            tenant_id=tenant_id,
            actual_scope_type=ROLE_SCOPE_TENANT,
            actual_scope_id=None,
            assigned_by=None,
            assigned_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
        )
    )
    revoked = RoleBinding.create(
        principal_id=user.id,
        role_id=planner.id,
        tenant_id=tenant_id,
        actual_scope_type=ROLE_SCOPE_TENANT,
    )
    repositories.role_binding_repo.add(revoked)
    services["session"].flush()
    repositories.role_binding_repo.revoke(revoked.id, revoked_at=now)
    services["session"].commit()

    authority = _resolver(services).resolve(
        user.id,
        tenant_id=tenant_id,
        organization_id=None,
    )

    assert authority.role_names == frozenset()
    assert authority.permissions == frozenset()


def test_scope_mismatch_fails_closed(services) -> None:
    repositories = _role_repositories(services)
    user, tenant_id = _create_user_without_legacy_roles(
        services,
        "canonical-resolver-scope-mismatch",
    )
    viewer = repositories.role_repo.get_by_name("viewer")
    assert viewer is not None
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=viewer.id,
            tenant_id=tenant_id,
            actual_scope_type="organization",
            actual_scope_id="organization-1",
        )
    )
    services["session"].commit()

    with pytest.raises(BusinessRuleError) as exc_info:
        _resolver(
            services,
            owned_scopes={
                "organization": {(tenant_id, "organization-1")},
            },
        ).resolve(
            user.id,
            tenant_id=tenant_id,
            organization_id="organization-1",
        )

    assert exc_info.value.code == "AUTH_ROLE_BINDING_SCOPE_MISMATCH"


def test_missing_resource_ownership_resolver_fails_closed(services) -> None:
    repositories = _role_repositories(services)
    user, tenant_id = _create_user_without_legacy_roles(
        services,
        "canonical-resolver-missing-owner-check",
    )
    project_role = Role.create(
        name="unresolved_project_role",
        is_system=False,
        tenant_id=tenant_id,
        allowed_scope_type="project",
    )
    repositories.role_repo.add(project_role)
    services["session"].flush()
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=project_role.id,
            tenant_id=tenant_id,
            actual_scope_type="project",
            actual_scope_id="project-1",
        )
    )
    services["session"].commit()

    with pytest.raises(BusinessRuleError) as exc_info:
        _resolver(services).resolve(
            user.id,
            tenant_id=tenant_id,
            organization_id=None,
        )

    assert exc_info.value.code == "AUTHORIZATION_SCOPE_RESOLVER_REQUIRED"
