"""Tests for tenant-switcher backend prerequisites: list_accessible_tenants + switch_to_tenant.

Covers:
  1. user can list only their accessible tenants (membership-based, no permission gate)
  2. inactive user_tenants membership is excluded from list_accessible_tenants
  3. suspended/archived tenant excluded for normal users
  4. tenant switch clears previous tenant's organization_id
  5. tenant switch auto-selects single accessible org in target tenant
  6. tenant switch leaves organization None if multiple/no orgs available
  7. switching to tenant without membership is denied
  8. platform admin/admin list_accessible_tenants returns all tenants
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.platform.application.tenant.tenancy.dto.commands.tenants import (
    TenantCreateCommand,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.tenant.tenancy.user_tenant_membership import (
    UserTenantMembership,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.admin import (
    TenantAdminDependencies,
    build_tenant_admin_dependencies,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
    SqlAlchemyTenantRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)
from src.tests.platform.tenancy_support import tenant_admin_operations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_regular_user_svc(
    services,
    *,
    username: str,
    tenant_id: str | None = None,
) -> tuple[TenantAdminDependencies, TenantContextService, UserSessionContext]:
    """Build TenantAdminDependencies + TenantContextService scoped to a fresh regular user."""
    session = services["session"]
    try:
        user = services["user_registration"].register_user(
            username, "StrongPass123!", role_names=["viewer"]
        )
    except Exception:
        user = services["authentication"].authenticate(username, "StrongPass123!")

    principal = services["principal_builder"].build(user)
    ctx = UserSessionContext()
    ctx.set_principal(principal)

    active_tenant_id = (
        tenant_id or services["tenant_context_service"].get_active_tenant_id()
    )
    if active_tenant_id:
        ctx.set_active_tenant_id(active_tenant_id)

    tenant_repo = SqlAlchemyTenantRepository(session)
    user_tenant_repo = SqlAlchemyUserTenantMembershipRepository(session)
    org_repo = SqlAlchemyOrganizationRepository(session)

    svc = build_tenant_admin_dependencies(
        session=session,
        repositories=SimpleNamespace(
            tenant_repo=tenant_repo,
            user_tenant_repo=user_tenant_repo,
            platform_event_repo=None,
        ),
        user_session=ctx,
    )
    context_svc = TenantContextService(
        tenant_repo=tenant_repo,
        organization_repo=org_repo,
        user_session=ctx,
        user_tenant_repo=user_tenant_repo,
    )
    return svc, context_svc, ctx


def _add_org(services, *, tenant_id: str, code: str, name: str) -> Organization:
    """Insert an active Organization directly, bypassing service permissions."""
    session = services["session"]
    org = Organization.create(code, name, tenant_id=tenant_id)
    org_repo = SqlAlchemyOrganizationRepository(session)
    org_repo.add(org)
    session.flush()
    return org


# ---------------------------------------------------------------------------
# 1. list_accessible_tenants — membership-based, no permission gate
# ---------------------------------------------------------------------------


def test_list_accessible_tenants_returns_user_memberships(services):
    admin_svc = tenant_admin_operations(services)
    t1 = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-USR1A", display_name="User1 Tenant A"))
    t2 = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-USR1B", display_name="User1 Tenant B"))
    services["session"].flush()

    svc, _, ctx = _make_regular_user_svc(services, username="p2d-accessible-user1")
    user_id = ctx.principal.user_id
    ut_repo = SqlAlchemyUserTenantMembershipRepository(services["session"])
    ut_repo.add(UserTenantMembership.create(user_id=user_id, tenant_id=t1.id))
    ut_repo.add(UserTenantMembership.create(user_id=user_id, tenant_id=t2.id))
    services["session"].flush()

    accessible = svc.tenant_admin_queries.list_accessible_tenants()
    accessible_ids = {t.id for t in accessible}
    assert t1.id in accessible_ids
    assert t2.id in accessible_ids


# ---------------------------------------------------------------------------
# 2. inactive membership excluded
# ---------------------------------------------------------------------------


def test_list_accessible_tenants_inactive_membership_excluded(services):
    admin_svc = tenant_admin_operations(services)
    t_active = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-MEMB-ACT", display_name="Member Active"))
    t_inactive = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-MEMB-INACT", display_name="Member Inactive"))
    services["session"].flush()

    svc, _, ctx = _make_regular_user_svc(services, username="p2d-membership-excl")
    user_id = ctx.principal.user_id
    ut_repo = SqlAlchemyUserTenantMembershipRepository(services["session"])
    ut_repo.add(UserTenantMembership.create(user_id=user_id, tenant_id=t_active.id))
    ut_repo.add(UserTenantMembership.create(user_id=user_id, tenant_id=t_inactive.id))
    services["session"].flush()

    ut_repo.update(ut_repo.get(user_id, t_inactive.id).suspend())
    services["session"].flush()

    accessible = svc.tenant_admin_queries.list_accessible_tenants()
    accessible_ids = {t.id for t in accessible}
    assert t_active.id in accessible_ids
    assert t_inactive.id not in accessible_ids


# ---------------------------------------------------------------------------
# 3. suspended/archived tenant excluded for regular users
# ---------------------------------------------------------------------------


def test_list_accessible_tenants_suspended_tenant_excluded(services):
    admin_svc = tenant_admin_operations(services)
    t_susp = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-SUSP-EXCL", display_name="Suspend Excl"))
    services["session"].flush()

    svc, _, ctx = _make_regular_user_svc(services, username="p2d-susp-excl-user")
    user_id = ctx.principal.user_id
    ut_repo = SqlAlchemyUserTenantMembershipRepository(services["session"])
    ut_repo.add(UserTenantMembership.create(user_id=user_id, tenant_id=t_susp.id))
    services["session"].flush()

    admin_svc.tenant_lifecycle_commands.suspend_tenant(t_susp.id)
    services["session"].flush()

    accessible = svc.tenant_admin_queries.list_accessible_tenants()
    assert t_susp.id not in {t.id for t in accessible}


def test_list_accessible_tenants_archived_tenant_excluded(services):
    admin_svc = tenant_admin_operations(services)
    t_arch = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-ARCH-EXCL", display_name="Archive Excl"))
    services["session"].flush()

    svc, _, ctx = _make_regular_user_svc(services, username="p2d-arch-excl-user")
    user_id = ctx.principal.user_id
    ut_repo = SqlAlchemyUserTenantMembershipRepository(services["session"])
    ut_repo.add(UserTenantMembership.create(user_id=user_id, tenant_id=t_arch.id))
    services["session"].flush()

    admin_svc.tenant_lifecycle_commands.archive_tenant(t_arch.id)
    services["session"].flush()

    accessible = svc.tenant_admin_queries.list_accessible_tenants()
    assert t_arch.id not in {t.id for t in accessible}


# ---------------------------------------------------------------------------
# 4. tenant switch clears previous tenant's organization_id
# ---------------------------------------------------------------------------


def test_switch_to_tenant_clears_previous_organization(services):
    tenant_context = services["tenant_context_service"]
    admin_svc = tenant_admin_operations(services)
    user_session = services["user_session"]

    current_org = tenant_context.get_active_organization()
    assert current_org is not None, (
        "Test requires a pre-set active org from default tenant"
    )

    new_tenant = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-SWITCH-CLR", display_name="Switch Clear Test"))
    services["session"].flush()

    tenant_context.switch_to_tenant(new_tenant.id)

    assert tenant_context.get_active_organization() is None
    assert user_session.active_organization_id() != current_org.id


# ---------------------------------------------------------------------------
# 5. tenant switch auto-selects single accessible org
# ---------------------------------------------------------------------------


def test_switch_to_tenant_auto_selects_single_org(services):
    tenant_context = services["tenant_context_service"]
    admin_svc = tenant_admin_operations(services)

    new_tenant = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-AUTOSEL", display_name="Auto Select Tenant"))
    services["session"].flush()
    the_org = _add_org(
        services,
        tenant_id=new_tenant.id,
        code="P2D-AUTOSEL-ORG",
        name="Auto Select Org",
    )

    tenant_context.switch_to_tenant(new_tenant.id)

    assert tenant_context.get_active_organization_id() == the_org.id


# ---------------------------------------------------------------------------
# 6. tenant switch leaves organization None if multiple/no orgs
# ---------------------------------------------------------------------------


def test_switch_to_tenant_leaves_org_none_if_no_orgs(services):
    tenant_context = services["tenant_context_service"]
    admin_svc = tenant_admin_operations(services)

    new_tenant = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-NOORG", display_name="No Org Tenant"))
    services["session"].flush()

    tenant_context.switch_to_tenant(new_tenant.id)

    assert tenant_context.get_active_organization_id() is None


def test_switch_to_tenant_leaves_org_none_if_multiple_orgs(services):
    tenant_context = services["tenant_context_service"]
    admin_svc = tenant_admin_operations(services)

    new_tenant = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-MULTORG", display_name="Multi Org Tenant"))
    services["session"].flush()
    _add_org(
        services, tenant_id=new_tenant.id, code="P2D-MULT-ORG1", name="Multi Org 1"
    )
    _add_org(
        services, tenant_id=new_tenant.id, code="P2D-MULT-ORG2", name="Multi Org 2"
    )

    tenant_context.switch_to_tenant(new_tenant.id)

    assert tenant_context.get_active_organization_id() is None


# ---------------------------------------------------------------------------
# 7. switching to tenant without membership is denied for regular user
# ---------------------------------------------------------------------------


def test_switch_to_tenant_without_membership_denied(services):
    admin_svc = tenant_admin_operations(services)
    locked_tenant = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-LOCKED", display_name="Locked Tenant"))
    services["session"].flush()

    _, context_svc, _ = _make_regular_user_svc(services, username="p2d-no-access-user")

    with pytest.raises(BusinessRuleError) as exc:
        context_svc.switch_to_tenant(locked_tenant.id)
    assert exc.value.code == "TENANT_ACCESS_DENIED"


# ---------------------------------------------------------------------------
# 8. platform.admin list_accessible_tenants returns all tenants
# ---------------------------------------------------------------------------


def test_platform_admin_list_accessible_tenants_returns_all(services):
    admin_svc = tenant_admin_operations(services)
    t1 = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-ADMIN-ALL1", display_name="Admin All 1"))
    t2 = admin_svc.tenant_lifecycle_commands.create_tenant(
        TenantCreateCommand(tenant_code="P2D-ADMIN-ALL2", display_name="Admin All 2"))
    admin_svc.tenant_lifecycle_commands.suspend_tenant(t2.id)
    services["session"].flush()

    accessible = admin_svc.tenant_admin_queries.list_accessible_tenants()
    accessible_ids = {t.id for t in accessible}

    assert t1.id in accessible_ids
    assert t2.id in accessible_ids  # platform.admin sees suspended tenants too
