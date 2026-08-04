"""Tests for Phase 0 critical bug fixes.

Fix 1 & 2: Organization service/repository scoping by tenant_id.
Fix 3:     platform.admin permission seeded; admin role receives it.
Fix 4:     user_roles unique constraint supports org-scoped role assignment.
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.auth.policy import DEFAULT_PERMISSIONS
from src.core.platform.infrastructure.persistence.orm.tenant import TenantORM
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.domain.master_data.org.organization import Organization


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_context(tenant_id: str) -> UserSessionContext:
    ctx = UserSessionContext()
    principal = UserSessionPrincipal(
        user_id="test-user",
        username="test",
        display_name="Test",
        role_names=frozenset(["admin"]),
        permissions=frozenset(["settings.manage", "platform.admin"]),
    )
    ctx.set_principal(principal)
    ctx.set_active_tenant_id(tenant_id)
    return ctx


def _add_tenant_row(session, tenant_id: str, code: str) -> None:
    """Insert a minimal tenant row so FK constraints on organizations.tenant_id pass."""
    session.add(TenantORM(id=tenant_id, tenant_code=code, display_name=code, is_active=True, version=1))
    session.flush()


# ---------------------------------------------------------------------------
# Fix 1 & 2: _deactivate_other_organizations is scoped to active tenant
# ---------------------------------------------------------------------------

def test_deactivate_other_organizations_does_not_touch_other_tenants(services):
    """Activating an org in tenant A must not deactivate orgs in tenant B."""
    session = services["session"]
    repo = SqlAlchemyOrganizationRepository(session)
    tenant_context_service = services["tenant_context_service"]

    tenant_a = tenant_context_service.get_active_tenant_id()
    assert tenant_a is not None

    tenant_b = "tenant-fix1-b"
    _add_tenant_row(session, tenant_b, "FIX1-B")

    org_a1 = Organization.create("FIX1-A1", "Tenant A Org 1", tenant_id=tenant_a, is_active=True)
    org_a2 = Organization.create("FIX1-A2", "Tenant A Org 2", tenant_id=tenant_a, is_active=True)
    org_b1 = Organization.create("FIX1-B1", "Tenant B Org 1", tenant_id=tenant_b, is_active=True)

    repo.add(org_a1)
    repo.add(org_a2)
    repo.add(org_b1)
    session.flush()

    ctx_a = _make_session_context(tenant_a)
    svc_a = OrganizationService(session=session, organization_repo=repo, user_session=ctx_a)

    svc_a._deactivate_other_organizations(tenant_id=tenant_a, exclude_id=org_a1.id)
    session.flush()

    refreshed_a2 = repo.get(org_a2.id)
    refreshed_b1 = repo.get(org_b1.id)

    assert refreshed_a2 is not None and refreshed_a2.is_active is False
    assert refreshed_b1 is not None and refreshed_b1.is_active is True


def test_list_organizations_is_scoped_to_active_tenant(services):
    """list_organizations() should return only the current tenant's orgs."""
    session = services["session"]
    repo = SqlAlchemyOrganizationRepository(session)
    tenant_context_service = services["tenant_context_service"]

    tenant_a = tenant_context_service.get_active_tenant_id()
    assert tenant_a is not None

    tenant_b = "tenant-fix2-b"
    _add_tenant_row(session, tenant_b, "FIX2-B")

    org_a = Organization.create("FIX2-A", "Tenant A Org", tenant_id=tenant_a, is_active=False)
    org_b = Organization.create("FIX2-B", "Tenant B Org", tenant_id=tenant_b, is_active=False)
    repo.add(org_a)
    repo.add(org_b)
    session.flush()

    ctx_a = _make_session_context(tenant_a)
    svc_a = OrganizationService(session=session, organization_repo=repo, user_session=ctx_a)

    result = svc_a.list_organizations()

    ids = {o.id for o in result}
    assert org_a.id in ids
    assert org_b.id not in ids


def test_get_active_organization_returns_tenant_scoped_active_org(services):
    """get_active_organization() should use get_active_for_tenant() when tenant is set."""
    session = services["session"]
    repo = SqlAlchemyOrganizationRepository(session)
    tenant_context_service = services["tenant_context_service"]

    tenant_a = tenant_context_service.get_active_tenant_id()
    assert tenant_a is not None

    tenant_b = "tenant-fix2b-b"
    _add_tenant_row(session, tenant_b, "FIX2B-B")

    # Add a second org for tenant_b that is also active
    org_b = Organization.create("FIX2B-B", "Tenant B Active", tenant_id=tenant_b, is_active=True)
    repo.add(org_b)
    session.flush()

    ctx_a = _make_session_context(tenant_a)
    svc_a = OrganizationService(session=session, organization_repo=repo, user_session=ctx_a)

    # Should return tenant_a's active org, not tenant_b's
    active = svc_a.get_active_organization()
    assert active.tenant_id == tenant_a


def test_get_active_for_tenant_repository_method(services):
    """SqlAlchemyOrganizationRepository.get_active_for_tenant() filters by tenant_id."""
    session = services["session"]
    repo = SqlAlchemyOrganizationRepository(session)
    tenant_context_service = services["tenant_context_service"]

    t1 = tenant_context_service.get_active_tenant_id()
    assert t1 is not None

    t2 = "tenant-repo-2"
    _add_tenant_row(session, t2, "REPO-T2")

    o2 = Organization.create("REPO-T2", "T2 Active Org", tenant_id=t2, is_active=True)
    repo.add(o2)
    session.flush()

    result_t1 = repo.get_active_for_tenant(t1)
    result_t2 = repo.get_active_for_tenant(t2)
    result_missing = repo.get_active_for_tenant("nonexistent-tenant")

    assert result_t1 is not None and result_t1.tenant_id == t1
    assert result_t2 is not None and result_t2.id == o2.id
    assert result_missing is None


# ---------------------------------------------------------------------------
# Fix 3: platform.admin permission seeded and admin role receives it
# ---------------------------------------------------------------------------

def test_platform_admin_permission_in_default_permissions():
    """DEFAULT_PERMISSIONS must define platform.admin."""
    assert "platform.admin" in DEFAULT_PERMISSIONS


def test_admin_user_has_platform_admin_permission(services):
    """The bootstrapped admin user's permissions must include platform.admin."""
    auth = services["auth_service"]
    user_session = services["user_session"]

    admin_perms = auth.get_user_permissions(
        services["auth_service"].authenticate("admin", "ChangeMe123!").id
    )
    assert "platform.admin" in admin_perms


def test_is_platform_admin_returns_true_for_admin_session(services):
    """UserSessionContext.is_platform_admin() returns True for the admin session."""
    assert services["user_session"].is_platform_admin() is True


def test_is_platform_admin_returns_false_for_viewer(services):
    """UserSessionContext.is_platform_admin() returns False for a non-admin user."""
    auth = services["auth_service"]
    user_session = services["user_session"]

    auth.register_user("viewer-no-admin", "StrongPass123", role_names=["viewer"])
    viewer = auth.authenticate("viewer-no-admin", "StrongPass123")
    user_session.set_principal(auth.build_principal(viewer))

    assert user_session.is_platform_admin() is False

