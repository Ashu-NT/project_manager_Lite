from __future__ import annotations

import pytest

from src.core.platform.access.authorization import require_scope_permission
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.modules.project_management.access.policy import resolve_project_scope_permissions
from src.core.platform.domain.master_data.site.access_policy import resolve_site_scope_permissions
from src.core.platform.domain.master_data.org.access_policy import (
    resolve_organization_scope_permissions,
)
from src.tests.ui_runtime_helpers import login_as


def _register_active_tenant_user(
    services,
    username: str,
    *,
    role_names: list[str],
):
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="prepare scoped-access test user"
    )
    return services["auth_service"].register_user(
        username,
        "StrongPass123",
        role_names=role_names,
        tenant_id=tenant_id,
    )


def test_user_session_supports_generic_scoped_access_and_project_compatibility():
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="scoped-user",
            display_name=None,
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"task.read", "inventory.read"}),
            scoped_access={
                "project": {"project-1": frozenset({"task.read"})},
                "storeroom": {"storeroom-1": frozenset({"inventory.read"})},
            },
        )
    )

    assert user_session.has_scope_permission("project", "project-1", "task.read") is True
    assert user_session.has_project_permission("project-1", "task.read") is True
    assert user_session.has_scope_permission("project", "project-2", "task.read") is False
    assert user_session.has_scope_permission("storeroom", "storeroom-1", "inventory.read") is True
    assert user_session.has_any_scope_access("storeroom", "inventory.read") is True
    assert user_session.scope_ids_for("storeroom", "inventory.read") == {"storeroom-1"}
    assert user_session.is_scope_restricted("project") is True
    assert user_session.is_project_restricted() is True
    assert user_session.principal is not None
    assert user_session.principal.project_access == {"project-1": frozenset({"task.read"})}


def test_require_scope_permission_uses_generic_scope_model():
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-2",
            username="project-reader",
            display_name=None,
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"task.read"}),
            scoped_access={"project": {"project-1": frozenset({"task.read"})}},
        )
    )

    require_scope_permission(
        user_session,
        "project",
        "project-1",
        "task.read",
        operation_label="view project tasks",
    )

    with pytest.raises(BusinessRuleError, match="project 'project-2'"):
        require_scope_permission(
            user_session,
            "project",
            "project-2",
            "task.read",
            operation_label="view project tasks",
        )


def test_access_service_supports_organization_scope_grants_and_principal_hydration(services):
    auth = services["auth_service"]
    access = services["access_service"]
    organization_service = services["organization_service"]

    org_a = organization_service.create_organization(
        organization_code="ACCESS-ORG-A", display_name="Access Scope Org A", is_enabled=True,
    )
    org_b = organization_service.create_organization(
        organization_code="ACCESS-ORG-B", display_name="Access Scope Org B", is_enabled=True,
    )
    user = _register_active_tenant_user(
        services,
        "organization-scope-user",
        role_names=["viewer"],
    )

    grant_a = access.assign_scope_grant(
        scope_type="organization", scope_id=org_a.id, user_id=user.id, scope_role="viewer",
    )
    grant_b = access.assign_scope_grant(
        scope_type="organization", scope_id=org_b.id, user_id=user.id, scope_role="member",
    )

    assert grant_a.scope_type == "organization"
    assert grant_a.permission_codes == sorted(resolve_organization_scope_permissions("viewer"))
    assert grant_b.permission_codes == sorted(resolve_organization_scope_permissions("member"))
    assert access.list_scope_role_choices("organization") == ("viewer", "member", "admin")
    assert "organization" in access.list_supported_scope_types()

    principal = auth.build_principal(user)
    assert principal.scoped_access["organization"][org_a.id] == frozenset(
        resolve_organization_scope_permissions("viewer")
    )
    assert principal.scoped_access["organization"][org_b.id] == frozenset(
        resolve_organization_scope_permissions("member")
    )
    # Adding B must not replace A -- both remain simultaneously granted.
    assert set(principal.scoped_access["organization"].keys()) == {org_a.id, org_b.id}

    listed_scope_grants = access.list_scope_grants("organization", org_a.id)
    listed_user_grants = access.list_user_scope_grants(user.id, scope_type="organization")
    assert len(listed_scope_grants) == 1
    assert listed_scope_grants[0].id == grant_a.id
    assert {row.id for row in listed_user_grants} == {grant_a.id, grant_b.id}

    access.remove_scope_grant(scope_type="organization", scope_id=org_a.id, user_id=user.id)
    principal_after_revoke = auth.build_principal(user)
    assert org_a.id not in principal_after_revoke.scoped_access.get("organization", {})
    assert org_b.id in principal_after_revoke.scoped_access.get("organization", {})


def test_access_service_rejects_organization_target_from_another_tenant(services):
    from src.core.platform.common.exceptions import NotFoundError
    from src.core.platform.domain.tenant.tenancy import Tenant
    from src.core.platform.domain.master_data.org import Organization
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
        SqlAlchemyTenantRepository,
    )

    other_tenant = Tenant.create(
        tenant_code="ACCESS-ORG-SCOPE-OTHER",
        display_name="Access Org Scope Other Tenant",
    )
    SqlAlchemyTenantRepository(services["session"]).add(other_tenant)
    services["session"].flush()
    foreign_org = Organization.create(
        organization_code="ACCESS-ORG-SCOPE-FOREIGN-ORG",
        display_name="Access Org Scope Foreign Organization",
        tenant_id=other_tenant.id,
    )
    services["organization_service"]._organization_repo.add(foreign_org)
    services["session"].flush()
    target = _register_active_tenant_user(
        services,
        "organization-scope-cross-tenant-target",
        role_names=["viewer"],
    )

    with pytest.raises(NotFoundError) as exc_info:
        services["access_service"].assign_scope_grant(
            scope_type="organization",
            scope_id=foreign_org.id,
            user_id=target.id,
            scope_role="viewer",
        )
    assert exc_info.value.code == "ORGANIZATION_NOT_FOUND"


def test_access_service_allows_organization_scope_grant_to_a_disabled_organization(services):

    access = services["access_service"]
    organization_service = services["organization_service"]
    disabled_org = organization_service.create_organization(
        organization_code="ACCESS-ORG-DISABLED",
        display_name="Access Scope Disabled Org",
        is_enabled=False,
    )
    user = _register_active_tenant_user(
        services,
        "organization-scope-disabled-org-user",
        role_names=["viewer"],
    )

    grant = access.assign_scope_grant(
        scope_type="organization",
        scope_id=disabled_org.id,
        user_id=user.id,
        scope_role="viewer",
    )

    assert grant.scope_id == disabled_org.id
    principal = services["auth_service"].build_principal(user)
    assert disabled_org.id in principal.scoped_access["organization"]


def test_access_service_rejects_target_from_another_tenant(services):
    project = services["project_service"].create_project(
        "Cross Tenant Access Target"
    )
    other_tenant = services["tenant_admin_service"].create_tenant(
        "ACCESS-TARGET",
        "Access Target Tenant",
    )
    target = services["auth_service"].register_user(
        "cross-tenant-membership-target",
        "StrongPass123",
        role_names=["viewer"],
        tenant_id=other_tenant.id,
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        services["access_service"].assign_scope_grant(
            scope_type="project",
            scope_id=project.id,
            user_id=target.id,
            scope_role="viewer",
        )

    assert exc_info.value.code == "ACCESS_TARGET_TENANT_DENIED"


def test_auth_build_principal_populates_generic_scoped_access_from_project_memberships(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Scoped Principal Project")
    user = _register_active_tenant_user(
        services,
        "scoped-principal-user",
        role_names=["viewer"],
    )

    access.assign_scope_grant(
        scope_type="project",
        scope_id=project.id,
        user_id=user.id,
        scope_role="viewer",
    )

    principal = auth.build_principal(user)

    assert principal.scoped_access["project"][project.id] == frozenset(
        resolve_project_scope_permissions("viewer")
    )
    assert principal.project_access[project.id] == principal.scoped_access["project"][project.id]


def test_access_service_supports_site_scope_grants_and_site_filtering(services):
    auth = services["auth_service"]
    access = services["access_service"]
    site_a = services["site_service"].create_site(
        site_code="SITE-A",
        name="Allowed Site",
        city="Berlin",
        currency_code="EUR",
    )
    services["site_service"].create_site(
        site_code="SITE-B",
        name="Blocked Site",
        city="Munich",
        currency_code="EUR",
    )
    user = _register_active_tenant_user(
        services,
        "site-scope-user",
        role_names=["inventory_manager"],
    )

    grant = access.assign_scope_grant(
        scope_type="site",
        scope_id=site_a.id,
        user_id=user.id,
        scope_role="manager",
    )

    assert grant.permission_codes == sorted(resolve_site_scope_permissions("manager"))
    principal = auth.build_principal(user)
    assert principal.scoped_access["site"][site_a.id] == frozenset(resolve_site_scope_permissions("manager"))

    login_as(services, "site-scope-user", "StrongPass123")
    visible_sites = services["site_service"].list_sites()

    assert [site.id for site in visible_sites] == [site_a.id]

