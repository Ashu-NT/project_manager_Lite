"""Tests for Phase 2B: TenantAdminService lifecycle operations.

Covers:
  1. Tenant.is_active is a derived property from tenant_status
  2. platform admin can create a tenant
  3. tenant_admin cannot create a tenant
  4. viewer (no tenant.create) is denied create_tenant
  5. duplicate tenant_code is rejected
  6. create_tenant does not seed a platform operator customer membership
  7. suspend_tenant: active → suspended
  8. cannot suspend an already-suspended tenant
  9. cannot suspend own active tenant (self-lockout guard)
  10. archive_tenant: active → archived
  11. archive_tenant: suspended → archived
  12. cannot archive an already-archived tenant
  13. cannot archive own active tenant (self-lockout guard)
  14. restore_tenant: archived → active (platform.admin only)
  15. tenant_admin cannot restore (platform.admin required)
  16. restore fails if tenant is not archived
  17. suspended tenant cannot be selected via set_active_tenant
  18. archived tenant cannot be selected via set_active_tenant
  19. list_tenants is denied to tenant_admin
  20. list_tenants denied for viewer
"""
from __future__ import annotations

import pytest

from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.infrastructure.persistence.repositories.tenant import SqlAlchemyTenantRepository
from src.core.platform.infrastructure.persistence.repositories.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)
from src.core.platform.tenancy.application.tenant_admin_service import TenantAdminService
from src.core.platform.tenancy.domain.tenant import (
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_ARCHIVED,
    TENANT_STATUS_SUSPENDED,
    Tenant,
)
from src.core.platform.tenancy.tenant_context import TenantContextService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_svc(services, *, role_names=None, permissions=None) -> TenantAdminService:
    """Build a TenantAdminService scoped to a new session context with the given principal."""
    session = services["session"]
    auth = services["auth_service"]

    if role_names is None and permissions is None:
        # Use the bootstrapped admin session directly
        return services["tenant_admin_service"]

    main_tenant_id = services["tenant_context_service"].get_active_tenant_id()
    username = f"p2b-user-{''.join(sorted(role_names or []))}"
    try:
        user = auth.register_user(
            username,
            "StrongPass123!",
            role_names=list(role_names or []),
            tenant_id=main_tenant_id,
        )
    except Exception:
        user = auth.authenticate(username, "StrongPass123!")

    principal = auth.build_principal(user)
    ctx = UserSessionContext()
    ctx.set_principal(principal)

    # Copy active tenant/org from main session so context is valid
    if main_tenant_id:
        ctx.set_active_tenant_id(main_tenant_id)

    return TenantAdminService(
        session=session,
        tenant_repo=SqlAlchemyTenantRepository(session),
        user_tenant_repo=SqlAlchemyUserTenantMembershipRepository(session),
        user_session=ctx,
    )


def _make_viewer_svc(services) -> TenantAdminService:
    return _make_svc(services, role_names=["viewer"])


def _make_tenant_admin_svc(services) -> TenantAdminService:
    return _make_svc(services, role_names=["tenant_admin"])


# ---------------------------------------------------------------------------
# 1. Domain: is_active derived from tenant_status
# ---------------------------------------------------------------------------

def test_tenant_is_active_derived_from_status():
    t = Tenant(id="x", tenant_code="T", display_name="T", tenant_status=TENANT_STATUS_ACTIVE)
    assert t.is_active is True

    t.tenant_status = TENANT_STATUS_SUSPENDED
    assert t.is_active is False

    t.tenant_status = TENANT_STATUS_ARCHIVED
    assert t.is_active is False


def test_tenant_create_defaults_to_active():
    t = Tenant.create(tenant_code="NEW", display_name="New")
    assert t.tenant_status == TENANT_STATUS_ACTIVE
    assert t.is_active is True


def test_tenant_create_with_explicit_status():
    t = Tenant.create(tenant_code="SUSP", display_name="Susp", tenant_status=TENANT_STATUS_SUSPENDED)
    assert t.tenant_status == TENANT_STATUS_SUSPENDED
    assert t.is_active is False


# ---------------------------------------------------------------------------
# 2. create_tenant — permissions and happy path
# ---------------------------------------------------------------------------

def test_admin_can_create_tenant(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-NEW1", "Phase 2B Tenant 1")
    assert tenant.id is not None
    assert tenant.tenant_code == "P2B-NEW1"
    assert tenant.tenant_status == TENANT_STATUS_ACTIVE
    assert tenant.is_active is True


def test_tenant_admin_role_cannot_create_tenant(services):
    svc = _make_tenant_admin_svc(services)
    with pytest.raises(BusinessRuleError) as exc:
        svc.create_tenant("P2B-TADMIN", "Tenant Admin Created")
    assert exc.value.code == "PERMISSION_DENIED"


def test_viewer_cannot_create_tenant(services):
    svc = _make_viewer_svc(services)
    with pytest.raises(BusinessRuleError) as exc:
        svc.create_tenant("P2B-DENIED", "Should Fail")
    assert exc.value.code == "PERMISSION_DENIED"


def test_create_tenant_code_uniqueness(services):
    svc = services["tenant_admin_service"]
    svc.create_tenant("P2B-UNIQ", "First")
    with pytest.raises(BusinessRuleError) as exc:
        svc.create_tenant("P2B-UNIQ", "Second")
    assert exc.value.code == "TENANT_CODE_CONFLICT"


def test_create_tenant_code_normalized_to_uppercase(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("p2b-lower", "Lower Code")
    assert tenant.tenant_code == "P2B-LOWER"


def test_create_tenant_does_not_seed_platform_operator_membership(services):
    svc = services["tenant_admin_service"]
    actor_id = services["user_session"].principal.user_id
    tenant = svc.create_tenant("P2B-NO-SEED", "No Implicit Membership")

    assert services["auth_service"]._user_tenant_repo.is_active_member(
        actor_id,
        tenant.id,
    ) is False


# ---------------------------------------------------------------------------
# 7–9. suspend_tenant
# ---------------------------------------------------------------------------

def test_suspend_active_tenant(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-SUSP1", "Suspend Test 1")
    result = svc.suspend_tenant(tenant.id)
    assert result.tenant_status == TENANT_STATUS_SUSPENDED
    assert result.is_active is False


def test_cannot_suspend_already_suspended(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-SUSP2", "Suspend Test 2")
    svc.suspend_tenant(tenant.id)
    with pytest.raises(BusinessRuleError) as exc:
        svc.suspend_tenant(tenant.id)
    assert exc.value.code == "TENANT_INVALID_TRANSITION"


def test_cannot_suspend_archived_tenant(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-SUSP3", "Suspend Test 3")
    svc.archive_tenant(tenant.id)
    with pytest.raises(BusinessRuleError) as exc:
        svc.suspend_tenant(tenant.id)
    assert exc.value.code == "TENANT_INVALID_TRANSITION"


def test_suspend_self_lockout_guard(services):
    """Cannot suspend the tenant that is currently active in the session."""
    session = services["session"]
    svc = services["tenant_admin_service"]
    tenant_context = services["tenant_context_service"]
    active_tenant_id = tenant_context.get_active_tenant_id()
    assert active_tenant_id is not None

    with pytest.raises(BusinessRuleError) as exc:
        svc.suspend_tenant(active_tenant_id)
    assert exc.value.code == "TENANT_SELF_LOCKOUT"


# ---------------------------------------------------------------------------
# 10–13. archive_tenant
# ---------------------------------------------------------------------------

def test_archive_active_tenant(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-ARCH1", "Archive Test 1")
    result = svc.archive_tenant(tenant.id)
    assert result.tenant_status == TENANT_STATUS_ARCHIVED
    assert result.is_active is False


def test_archive_suspended_tenant(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-ARCH2", "Archive Test 2")
    svc.suspend_tenant(tenant.id)
    result = svc.archive_tenant(tenant.id)
    assert result.tenant_status == TENANT_STATUS_ARCHIVED


def test_cannot_archive_already_archived(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-ARCH3", "Archive Test 3")
    svc.archive_tenant(tenant.id)
    with pytest.raises(BusinessRuleError) as exc:
        svc.archive_tenant(tenant.id)
    assert exc.value.code == "TENANT_ALREADY_ARCHIVED"


def test_archive_self_lockout_guard(services):
    tenant_context = services["tenant_context_service"]
    active_tenant_id = tenant_context.get_active_tenant_id()
    svc = services["tenant_admin_service"]
    with pytest.raises(BusinessRuleError) as exc:
        svc.archive_tenant(active_tenant_id)
    assert exc.value.code == "TENANT_SELF_LOCKOUT"


# ---------------------------------------------------------------------------
# 14–16. restore_tenant
# ---------------------------------------------------------------------------

def test_admin_can_restore_archived_tenant(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-REST1", "Restore Test 1")
    svc.archive_tenant(tenant.id)
    result = svc.restore_tenant(tenant.id)
    assert result.tenant_status == TENANT_STATUS_ACTIVE
    assert result.is_active is True


def test_tenant_admin_cannot_restore(services):
    svc_admin = services["tenant_admin_service"]
    tenant = svc_admin.create_tenant("P2B-REST2", "Restore Test 2")
    svc_admin.archive_tenant(tenant.id)

    svc_tadmin = _make_tenant_admin_svc(services)
    with pytest.raises(BusinessRuleError) as exc:
        svc_tadmin.restore_tenant(tenant.id)
    assert exc.value.code == "PERMISSION_DENIED"


def test_restore_fails_if_not_archived(services):
    svc = services["tenant_admin_service"]
    tenant = svc.create_tenant("P2B-REST3", "Restore Test 3")
    with pytest.raises(BusinessRuleError) as exc:
        svc.restore_tenant(tenant.id)
    assert exc.value.code == "TENANT_NOT_ARCHIVED"


# ---------------------------------------------------------------------------
# 17–18. set_active_tenant rejects suspended/archived
# ---------------------------------------------------------------------------

def test_suspended_tenant_cannot_be_selected(services):
    svc = services["tenant_admin_service"]
    tenant_context = services["tenant_context_service"]
    tenant = svc.create_tenant("P2B-SELSUSP", "Select Suspend Test")
    svc.suspend_tenant(tenant.id)

    with pytest.raises(BusinessRuleError) as exc:
        tenant_context.set_active_tenant(tenant.id)
    assert exc.value.code == "TENANT_SUSPENDED"


def test_archived_tenant_cannot_be_selected(services):
    svc = services["tenant_admin_service"]
    tenant_context = services["tenant_context_service"]
    tenant = svc.create_tenant("P2B-SELARCH", "Select Archive Test")
    svc.archive_tenant(tenant.id)

    with pytest.raises(BusinessRuleError) as exc:
        tenant_context.set_active_tenant(tenant.id)
    assert exc.value.code == "TENANT_ARCHIVED"


# ---------------------------------------------------------------------------
# 19–20. list_tenants
# ---------------------------------------------------------------------------

def test_tenant_admin_cannot_list_tenants(services):
    svc_admin = services["tenant_admin_service"]
    svc_admin.create_tenant("P2B-LIST1", "List Test 1")
    svc_admin.create_tenant("P2B-LIST2", "List Test 2")

    svc_tadmin = _make_tenant_admin_svc(services)
    with pytest.raises(BusinessRuleError) as exc:
        svc_tadmin.list_tenants()
    assert exc.value.code == "PERMISSION_DENIED"


def test_viewer_cannot_list_tenants(services):
    svc = _make_viewer_svc(services)
    with pytest.raises(BusinessRuleError) as exc:
        svc.list_tenants()
    assert exc.value.code == "PERMISSION_DENIED"
