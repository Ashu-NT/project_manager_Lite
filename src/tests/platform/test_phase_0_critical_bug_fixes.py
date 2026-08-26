"""Tests for Phase 0 critical bug fixes.

Fix 1 & 2: Organization service/repository scoping by tenant_id.
Fix 3:     platform.admin permission seeded; admin role receives it.
Fix 4:     user_roles unique constraint supports org-scoped role assignment.
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_PERMISSIONS,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.domain.master_data.org.organization import Organization
from src.core.platform.infrastructure.persistence.organization_unit_of_work import (
    SqlAlchemyOrganizationUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_organization_uow_factory(session, tenant_context_service, user_session):
    """P4B: mirrors `platform_registry.py`'s own `organization_uow_factory` construction --
    derived from `session.bind` so it resolves to the test's isolated engine, never a real,
    on-disk database."""
    return SqlAlchemyOrganizationUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )


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


def test_list_organizations_is_scoped_to_active_tenant(services):
    """list_organizations() should return only the current tenant's orgs."""
    session = services["session"]
    repo = SqlAlchemyOrganizationRepository(session)
    tenant_context_service = services["tenant_context_service"]

    tenant_a = tenant_context_service.get_active_tenant_id()
    assert tenant_a is not None

    tenant_b = "tenant-fix2-b"
    _add_tenant_row(session, tenant_b, "FIX2-B")

    org_a = Organization.create("FIX2-A", "Tenant A Org", tenant_id=tenant_a, is_enabled=False)
    org_b = Organization.create("FIX2-B", "Tenant B Org", tenant_id=tenant_b, is_enabled=False)
    repo.add(org_a)
    repo.add(org_b)
    session.flush()

    ctx_a = _make_session_context(tenant_a)
    svc_a = OrganizationService(
        session=session,
        organization_repo=repo,
        uow_factory=_make_organization_uow_factory(session, tenant_context_service, ctx_a),
        clock=SystemClock(),
        user_session=ctx_a,
    )

    result = svc_a.list_organizations()

    ids = {o.id for o in result}
    assert org_a.id in ids
    assert org_b.id not in ids


# P10A: `OrganizationService.get_active_organization()` and
# `OrganizationRepository.get_active_for_tenant()` are deleted entirely -- both represented "the
# one tenant-wide active organization," a concept with no room in the corrected multi-org model
# (more than one organization may be enabled per tenant at once). The real runtime "current
# organization" resolution has always gone through `TenantContextService.get_active_organization()`
# (unaffected by this deletion; see test_p10a_organization_availability_model.py's structural
# guards and test_organization_platform_foundation.py's behavioral coverage), so
# `test_get_active_organization_returns_tenant_scoped_active_org` and
# `test_get_active_for_tenant_repository_method` are retired without replacement.


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

