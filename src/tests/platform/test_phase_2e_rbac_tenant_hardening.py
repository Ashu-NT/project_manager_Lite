"""Tests for Phase 2E: RBAC and Tenant Hardening.

Covers:
  C-1  Canonical delegation replaces role-name privilege ranks
  C-2  Tenant-scoped assignment / revocation rejects cross-tenant targets
  H-7  suspend_tenant / archive_tenant restricted to platform.admin
  H-8  User admin operations respect tenant boundaries
  H-5  _can_access() null bypass removal
  H-3  Stale org restore prevented when principal has no tenant
  H-4  Principal builder clears org when no tenant recorded
  H-2  active_organization_id() fallback validates tenant context
  H-6  OrganizationORM.tenant_id is NOT NULL
"""
from __future__ import annotations

from contextlib import contextmanager

import pytest

from src.core.platform.domain.security.authorization.roles import RoleBinding
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
    SqlAlchemyTenantRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)
from src.core.platform.application.tenant.tenancy.tenant_admin_service import TenantAdminService
from src.core.platform.domain.tenant.tenancy.tenant import Tenant
from src.core.platform.domain.tenant.tenancy.user_tenant_membership import UserTenantMembership
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_auth_svc(services, *, role_names):
    """Return (AuthService, user) with a non-admin session for the given roles."""
    from src.core.platform.application.security.auth import AuthService

    session = services["session"]
    auth = services["auth_service"]
    user_tenant_repo = SqlAlchemyUserTenantMembershipRepository(session)
    organization_repo = SqlAlchemyOrganizationRepository(session)
    active_tenant_id = services["tenant_context_service"].get_active_tenant_id()

    username = f"p2e-{''.join(sorted(role_names))}-{abs(id(role_names)) % 10000}"
    registration_roles = [
        role_name for role_name in role_names if role_name != "org_admin"
    ] or ["viewer"]
    try:
        user = auth.register_user(
            username,
            "StrongPass123!",
            role_names=registration_roles,
        )
    except Exception:
        user = auth.authenticate(username, "StrongPass123!")

    if active_tenant_id:
        try:
            user_tenant_repo.add(
                UserTenantMembership.create(
                    user_id=user.id,
                    tenant_id=active_tenant_id,
                )
            )
            session.flush()
        except Exception:
            pass

    if "org_admin" in role_names:
        active_organization_id = (
            services["tenant_context_service"].get_active_organization_id()
        )
        org_admin_role = auth._role_repo.get_by_name("org_admin")
        if (
            active_organization_id is not None
            and org_admin_role is not None
            and auth._role_binding_repo.get_active_for_assignment(
                principal_id=user.id,
                role_id=org_admin_role.id,
                tenant_id=active_tenant_id,
                actual_scope_type="organization",
                actual_scope_id=active_organization_id,
            ) is None
        ):
            auth._role_binding_repo.add(
                RoleBinding.create(
                    principal_id=user.id,
                    role_id=org_admin_role.id,
                    tenant_id=active_tenant_id,
                    actual_scope_type="organization",
                    actual_scope_id=active_organization_id,
                )
            )
            session.flush()

    principal = auth.build_principal(user)
    ctx = UserSessionContext()
    ctx.set_principal(principal)
    if active_tenant_id:
        ctx.set_active_tenant_id(active_tenant_id)

    svc = AuthService(
        session=session,
        user_repo=auth._user_repo,
        role_repo=auth._role_repo,
        permission_repo=auth._permission_repo,
        role_permission_repo=auth._role_permission_repo,
        role_binding_repo=auth._role_binding_repo,
        canonical_scope_tenant_resolvers={
            "organization": lambda tenant_id, organization_id: (
                organization_repo.get_for_tenant(
                    organization_id,
                    tenant_id,
                )
                is not None
            )
        },
        auth_session_repo=auth._auth_session_repo,
        user_tenant_repo=user_tenant_repo,
        user_session=ctx,
        security_audit_repo=auth._security_audit_repo,
        tenant_context_service=services["tenant_context_service"],
    )
    return svc, user


def _make_tenant_admin_svc(services, *, role_names=None):
    """Return a TenantAdminService with a session for the given roles, or admin if None."""
    if role_names is None:
        return services["tenant_admin_service"]

    session = services["session"]
    auth = services["auth_service"]
    active_tenant_id = services["tenant_context_service"].get_active_tenant_id()

    username = f"p2e-tas-{''.join(sorted(role_names))}"
    try:
        user = auth.register_user(username, "StrongPass123!", role_names=list(role_names))
    except Exception:
        user = auth.authenticate(username, "StrongPass123!")

    principal = auth.build_principal(user)
    ctx = UserSessionContext()
    ctx.set_principal(principal)
    if active_tenant_id:
        ctx.set_active_tenant_id(active_tenant_id)

    return TenantAdminService(
        session=session,
        tenant_repo=SqlAlchemyTenantRepository(session),
        user_tenant_repo=SqlAlchemyUserTenantMembershipRepository(session),
        user_session=ctx,
    )


def _register_in_tenant(session, user_id, tenant_id):
    repo = SqlAlchemyUserTenantMembershipRepository(session)
    try:
        repo.add(UserTenantMembership.create(user_id=user_id, tenant_id=tenant_id))
        session.flush()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# C-1/C-2: Canonical governance replaces rank and forbids cross-tenant targets
# ---------------------------------------------------------------------------

class TestTenantScopedRoleAssignment:
    def _cross_tenant_user(self, services):
        session = services["session"]
        admin_auth = services["auth_service"]
        tenant_repo = SqlAlchemyTenantRepository(session)

        tenant_b = Tenant.create(tenant_code="P2EC2-TB", display_name="Tenant B C2")
        tenant_repo.add(tenant_b)
        session.flush()

        user_b = admin_auth.register_user("p2e-c2-ub", "StrongPass123!")
        _register_in_tenant(session, user_b.id, tenant_b.id)
        return user_b

    def test_cross_tenant_role_assignment_is_denied(self, services):
        user_b = self._cross_tenant_user(services)
        with pytest.raises(BusinessRuleError) as exc_info:
            services["auth_service"].assign_role(user_b.id, "viewer")
        assert exc_info.value.code == "ROLE_TARGET_TENANT_DENIED"

    def test_cross_tenant_role_revocation_is_denied(self, services):
        user_b = self._cross_tenant_user(services)
        with pytest.raises(BusinessRuleError) as exc_info:
            services["auth_service"].revoke_role(user_b.id, "viewer")
        assert exc_info.value.code == "ROLE_TARGET_TENANT_DENIED"

    def test_local_platform_admin_does_not_bypass_target_membership(self, services):
        user_b = self._cross_tenant_user(services)
        with pytest.raises(BusinessRuleError) as exc_info:
            services["auth_service"].assign_role(user_b.id, "viewer")
        assert exc_info.value.code == "ROLE_TARGET_TENANT_DENIED"


# ---------------------------------------------------------------------------
# H-7: suspend / archive requires platform.admin only
# ---------------------------------------------------------------------------

class TestTenantLifecycleScope:
    def _create_tenant(self, services, code, name):
        session = services["session"]
        tenant_repo = SqlAlchemyTenantRepository(session)
        t = Tenant.create(tenant_code=code, display_name=name)
        tenant_repo.add(t)
        session.flush()
        return t

    def test_tenant_admin_cannot_suspend_tenant(self, services):
        target = self._create_tenant(services, "P2E-H7S", "H7 Suspend")
        svc = _make_tenant_admin_svc(services, role_names=["tenant_admin"])
        with pytest.raises(Exception):
            svc.suspend_tenant(target.id)

    def test_tenant_admin_cannot_archive_tenant(self, services):
        target = self._create_tenant(services, "P2E-H7A", "H7 Archive")
        svc = _make_tenant_admin_svc(services, role_names=["tenant_admin"])
        with pytest.raises(Exception):
            svc.archive_tenant(target.id)

    def test_platform_admin_can_suspend_tenant(self, services):
        target = self._create_tenant(services, "P2E-H7S2", "H7 Suspend 2")
        result = services["tenant_admin_service"].suspend_tenant(target.id)
        assert result.tenant_status == "suspended"

    def test_platform_admin_can_archive_tenant(self, services):
        target = self._create_tenant(services, "P2E-H7A2", "H7 Archive 2")
        result = services["tenant_admin_service"].archive_tenant(target.id)
        assert result.tenant_status == "archived"


# ---------------------------------------------------------------------------
# H-8: User admin operations respect tenant boundaries
# ---------------------------------------------------------------------------

class TestUserAdminTenantBoundary:
    def _cross_tenant_user(self, services, suffix=""):
        session = services["session"]
        admin_auth = services["auth_service"]
        tenant_repo = SqlAlchemyTenantRepository(session)

        t = Tenant.create(tenant_code=f"P2EH8{suffix}", display_name=f"H8 Tenant {suffix}")
        tenant_repo.add(t)
        session.flush()

        user = admin_auth.register_user(f"p2e-h8-cu{suffix}", "StrongPass123!")
        _register_in_tenant(session, user.id, t.id)
        return user

    def test_org_admin_cannot_set_user_active_cross_tenant(self, services):
        cross = self._cross_tenant_user(services, "A")
        svc, _ = _make_auth_svc(services, role_names=["org_admin"])
        with pytest.raises(BusinessRuleError) as exc_info:
            svc.set_user_active(cross.id, False)
        assert exc_info.value.code == "USER_CROSS_TENANT_DENIED"

    def test_org_admin_cannot_update_profile_cross_tenant(self, services):
        cross = self._cross_tenant_user(services, "B")
        svc, _ = _make_auth_svc(services, role_names=["org_admin"])
        with pytest.raises(BusinessRuleError) as exc_info:
            svc.update_user_profile(cross.id, display_name="Hacked")
        assert exc_info.value.code == "USER_CROSS_TENANT_DENIED"

    def test_org_admin_cannot_unlock_account_cross_tenant(self, services):
        cross = self._cross_tenant_user(services, "C")
        svc, _ = _make_auth_svc(services, role_names=["org_admin"])
        with pytest.raises(BusinessRuleError) as exc_info:
            svc.unlock_user_account(cross.id)
        assert exc_info.value.code == "USER_CROSS_TENANT_DENIED"

    def test_admin_can_set_user_active_cross_tenant(self, services):
        cross = self._cross_tenant_user(services, "D")
        result = services["auth_service"].set_user_active(cross.id, False)
        assert result.is_active is False

    def test_org_admin_can_manage_same_tenant_user(self, services):
        session = services["session"]
        svc, _ = _make_auth_svc(services, role_names=["org_admin"])
        admin_auth = services["auth_service"]
        active_tid = services["tenant_context_service"].get_active_tenant_id()

        same_user = admin_auth.register_user("p2e-h8-same", "StrongPass123!")
        _register_in_tenant(session, same_user.id, active_tid)

        result = svc.update_user_profile(same_user.id, display_name="Updated")
        assert result.display_name == "Updated"


# ---------------------------------------------------------------------------
# H-5: _can_access() null bypass removal
# ---------------------------------------------------------------------------

class TestCanAccessNullBypass:
    def _make_ctx_svc(self, session, active_tenant_id):
        from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
            SqlAlchemyOrganizationRepository,
        )
        ctx = UserSessionContext()
        ctx.set_active_tenant_id(active_tenant_id)
        return TenantContextService(
            tenant_repo=SqlAlchemyTenantRepository(session),
            organization_repo=SqlAlchemyOrganizationRepository(session),
            user_session=ctx,
        )

    def test_org_with_null_tenant_id_denied_when_session_has_tenant(self, services):
        """H-5: org.tenant_id=None is rejected when active tenant is set."""
        from src.core.platform.domain.master_data.org.organization import Organization

        active_tid = services["tenant_context_service"].get_active_tenant_id()
        svc = self._make_ctx_svc(services["session"], active_tid)
        org = Organization.create("H5-O1", "H5 Org 1", tenant_id=None)
        assert svc._can_access(org) is False

    def test_org_with_wrong_tenant_id_denied(self, services):
        """_can_access rejects orgs that belong to a different tenant."""
        from src.core.platform.domain.master_data.org.organization import Organization

        svc = self._make_ctx_svc(services["session"], "tenant-A")
        org = Organization.create("H5-O2", "H5 Org 2", tenant_id="tenant-B")
        assert svc._can_access(org) is False

    def test_org_with_matching_tenant_id_allowed(self, services):
        """_can_access allows orgs that match the active tenant (no principal check)."""
        from src.core.platform.domain.master_data.org.organization import Organization

        active_tid = services["tenant_context_service"].get_active_tenant_id()
        svc = self._make_ctx_svc(services["session"], active_tid)
        org = Organization.create("H5-O3", "H5 Org 3", tenant_id=active_tid)
        assert svc._can_access(org) is True

    def test_org_tenant_check_skipped_when_no_active_tenant(self, services):
        """_can_access is not restricted when no tenant is active (single-tenant mode)."""
        from src.core.platform.domain.master_data.org.organization import Organization
        from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
            SqlAlchemyOrganizationRepository,
        )

        session = services["session"]
        ctx = UserSessionContext()
        svc = TenantContextService(
            tenant_repo=SqlAlchemyTenantRepository(session),
            organization_repo=SqlAlchemyOrganizationRepository(session),
            user_session=ctx,
        )
        org = Organization.create("H5-O4", "H5 Org 4", tenant_id=None)
        assert svc._can_access(org) is True


# ---------------------------------------------------------------------------
# H-3: Stale org NOT restored when principal has no tenant
# ---------------------------------------------------------------------------

class TestStaleOrgRestore:
    def test_org_not_restored_when_principal_has_no_tenant(self):
        """H-3: principal with org but no tenant_id must NOT write org into session state
        when the session already has an active tenant set."""
        ctx = UserSessionContext()
        ctx.set_active_tenant_id("tenant-A")
        ctx.set_active_organization_id(None)

        stale_principal = UserSessionPrincipal(
            user_id="u-h3",
            username="user-h3",
            display_name=None,
            role_names=frozenset(["viewer"]),
            permissions=frozenset(),
            active_tenant_id=None,        # no tenant recorded
            active_organization_id="stale-org",
        )

        ctx._restore_active_context_from_principal(stale_principal)

        assert ctx.stored_active_organization_id() is None

    def test_org_restored_when_tenant_matches(self):
        """When principal.tenant matches session tenant, org IS correctly restored."""
        ctx = UserSessionContext()
        ctx.set_active_tenant_id("tenant-A")
        ctx.set_active_organization_id(None)

        principal = UserSessionPrincipal(
            user_id="u-h3b",
            username="user-h3b",
            display_name=None,
            role_names=frozenset(["viewer"]),
            permissions=frozenset(),
            active_tenant_id="tenant-A",
            active_organization_id="org-A",
        )

        ctx._restore_active_context_from_principal(principal)

        assert ctx.stored_active_organization_id() == "org-A"


# ---------------------------------------------------------------------------
# H-4: Principal builder clears org when no tenant is recorded in AuthSession
# ---------------------------------------------------------------------------

class TestPrincipalBuilderOrgClearing:
    def test_local_principal_establishes_default_context_when_session_has_none(self, services):
        """Local mode establishes its explicit default context during rebuild."""
        from unittest.mock import MagicMock, patch
        from src.core.platform.application.security.auth.session.principal_builder import build_principal

        auth = services["auth_service"]
        if auth._auth_session_repo is None:
            pytest.skip("auth_session_repo not wired — H-4 only applies when sessions are persisted")

        user = auth.register_user("p2e-h4-u1", "StrongPass123!")

        mock_session = MagicMock()
        mock_session.revoked_at = None
        mock_session.expires_at = user.session_expires_at
        mock_session.auth_method = "password"
        mock_session.last_active_tenant_id = None
        mock_session.last_active_organization_id = "stale-org"

        with patch.object(auth._auth_session_repo, "get", return_value=mock_session):
            principal = build_principal(auth, user, session_id="fake-sid-1")

        assert principal.active_tenant_id is not None
        assert principal.active_organization_id is not None

    def test_principal_rejects_unknown_saved_tenant(self, services):
        """Unknown saved tenant IDs are not restored as authorization context."""
        from unittest.mock import MagicMock, patch
        from src.core.platform.application.security.auth.session.principal_builder import build_principal

        auth = services["auth_service"]
        if auth._auth_session_repo is None:
            pytest.skip("auth_session_repo not wired — H-4 only applies when sessions are persisted")

        user = auth.register_user("p2e-h4-u2", "StrongPass123!")

        mock_session = MagicMock()
        mock_session.revoked_at = None
        mock_session.expires_at = user.session_expires_at
        mock_session.auth_method = "password"
        mock_session.last_active_tenant_id = "tenant-A"
        mock_session.last_active_organization_id = "org-A"

        with (
            patch.object(auth._auth_session_repo, "get", return_value=mock_session),
            pytest.raises(NotFoundError, match="Tenant not found"),
        ):
            build_principal(auth, user, session_id="fake-sid-2")


# ---------------------------------------------------------------------------
# H-2: active_organization_id() fallback validates tenant context
# ---------------------------------------------------------------------------

class TestActiveOrganizationIdTenantGuard:
    def test_principal_org_not_returned_when_tenant_mismatch(self):
        """H-2: org fallback from principal is suppressed when session tenant differs."""
        ctx = UserSessionContext()
        ctx._principal = UserSessionPrincipal(
            user_id="u-h2a",
            username="u-h2a",
            display_name=None,
            role_names=frozenset(["viewer"]),
            permissions=frozenset(),
            active_tenant_id="tenant-A",
            active_organization_id="org-A",
        )
        ctx._active_organization_id = None
        ctx._active_tenant_id = "tenant-B"

        assert ctx.active_organization_id() is None

    def test_principal_org_returned_when_tenant_matches(self):
        """H-2: org fallback from principal is returned when tenants are consistent."""
        ctx = UserSessionContext()
        ctx._principal = UserSessionPrincipal(
            user_id="u-h2b",
            username="u-h2b",
            display_name=None,
            role_names=frozenset(["viewer"]),
            permissions=frozenset(),
            active_tenant_id="tenant-A",
            active_organization_id="org-A",
        )
        ctx._active_organization_id = None
        ctx._active_tenant_id = "tenant-A"

        assert ctx.active_organization_id() == "org-A"

    def test_principal_org_returned_when_session_has_no_tenant(self):
        """H-2: org fallback from principal is returned in single-tenant mode."""
        ctx = UserSessionContext()
        ctx._principal = UserSessionPrincipal(
            user_id="u-h2c",
            username="u-h2c",
            display_name=None,
            role_names=frozenset(["viewer"]),
            permissions=frozenset(),
            active_tenant_id="tenant-A",
            active_organization_id="org-A",
        )
        ctx._active_organization_id = None
        ctx._active_tenant_id = None

        assert ctx.active_organization_id() == "org-A"


# ---------------------------------------------------------------------------
# H-6: OrganizationORM.tenant_id is NOT NULL
# ---------------------------------------------------------------------------

def test_organization_orm_tenant_id_is_not_nullable():
    """H-6: OrganizationORM.tenant_id must be NOT NULL (DB constraint aligned with ORM)."""
    from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM

    col = OrganizationORM.__table__.c["tenant_id"]
    assert col.nullable is False, "tenant_id must be NOT NULL after H-6 fix"
