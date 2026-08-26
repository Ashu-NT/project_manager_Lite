from __future__ import annotations

from src.tests.ui_runtime_helpers import login_as


def _register_active_tenant_user(services, username: str, *, role_names: list[str]):
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="prepare session restore test user"
    )
    return services["auth_service"].register_user(
        username, "StrongPass123", role_names=role_names, tenant_id=tenant_id
    )


def _grant(services, *, user_id: str, organization_id: str, scope_role: str = "viewer"):
    services["access_service"].assign_scope_grant(
        scope_type="organization", scope_id=organization_id, user_id=user_id, scope_role=scope_role
    )


def _login_admin(services) -> None:
    auth = services["auth_service"]
    user = auth.authenticate("admin", "ChangeMe123!")
    services["user_session"].set_principal(auth.build_principal(user))


# ----------------------------------------------------------------------
# 1. grant Org A -> login -> A valid
# ----------------------------------------------------------------------


def test_granted_organization_is_valid_on_login(services):
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-GRANT-A", display_name="Sec Grant A", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-grant-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)

    login_as(services, "sec-grant-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org_a.id)

    assert services["tenant_context_service"].get_active_organization_id() == org_a.id


# ----------------------------------------------------------------------
# 2. revoke Org A -> new login -> A NOT restored
# ----------------------------------------------------------------------


def test_revoked_organization_is_not_restored_on_a_new_login(services):
    access = services["access_service"]
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-REVOKE-RELOGIN-A", display_name="Sec Revoke Relogin A", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-revoke-relogin-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)

    login_as(services, "sec-revoke-relogin-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org_a.id)
    assert services["tenant_context_service"].get_active_organization_id() == org_a.id

    _login_admin(services)
    access.remove_scope_grant(scope_type="organization", scope_id=org_a.id, user_id=user.id)

    login_as(services, "sec-revoke-relogin-user", "StrongPass123")

    assert services["user_session"].principal.scoped_access.get("organization", {}) == {}
    assert services["tenant_context_service"].get_active_organization_id() != org_a.id
    assert services["tenant_context_service"].get_active_organization_id() is None


# ----------------------------------------------------------------------
# 3. revoked org cannot become active manually
# ----------------------------------------------------------------------


def test_revoked_organization_cannot_be_switched_to_manually(services):
    import pytest

    from src.core.platform.common.exceptions import BusinessRuleError

    access = services["access_service"]
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-REVOKE-MANUAL-A", display_name="Sec Revoke Manual A", is_enabled=True
    )
    other = organization_service.create_organization(
        organization_code="SEC-REVOKE-MANUAL-OTHER", display_name="Sec Revoke Manual Other", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-revoke-manual-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)
    _grant(services, user_id=user.id, organization_id=other.id)

    login_as(services, "sec-revoke-manual-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(other.id)

    _login_admin(services)
    access.remove_scope_grant(scope_type="organization", scope_id=org_a.id, user_id=user.id)

    login_as(services, "sec-revoke-manual-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(other.id)

    with pytest.raises(BusinessRuleError) as exc_info:
        services["tenant_context_service"].set_active_organization(org_a.id)
    assert exc_info.value.code == "PERMISSION_DENIED"


# ----------------------------------------------------------------------
# 4. persisted disabled org not restored
# ----------------------------------------------------------------------


def test_persisted_disabled_organization_is_not_restored(services):
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-DISABLED-RESTORE-A", display_name="Sec Disabled Restore A", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-disabled-restore-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)

    login_as(services, "sec-disabled-restore-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org_a.id)

    _login_admin(services)
    organization_service.disable_organization(org_a.id)

    login_as(services, "sec-disabled-restore-user", "StrongPass123")

    assert services["tenant_context_service"].get_active_organization_id() != org_a.id


# ----------------------------------------------------------------------
# 5. persisted cross-tenant org not restored
# ----------------------------------------------------------------------


def test_persisted_cross_tenant_organization_is_not_restored(services):
    """`validate_principal_context`'s pre-existing tenant-ownership check (`ORGANIZATION_TENANT_
    MISMATCH`) is what actually guards this -- unrelated to P10C-SEC's own RBAC check, but
    re-verified here since it sits on the exact same restore path this phase modified. A normal
    switch can never produce this state (it always requires the org to belong to the active
    tenant), so it is reproduced directly on the persisted `AuthSession` record, the same way a
    stale/corrupted persisted value could arise in practice."""
    from src.core.platform.domain.tenant.tenancy import Tenant
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
        SqlAlchemyTenantRepository,
    )

    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-CROSS-TENANT-A", display_name="Sec Cross Tenant A", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-cross-tenant-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)

    login_as(services, "sec-cross-tenant-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org_a.id)

    foreign_tenant = Tenant.create(tenant_code="SEC-CROSS-TENANT-FOREIGN", display_name="Sec Cross Tenant Foreign")
    SqlAlchemyTenantRepository(services["session"]).add(foreign_tenant)
    services["session"].flush()
    from src.core.platform.domain.master_data.org import Organization

    foreign_org_obj = Organization.create(
        organization_code="SEC-CROSS-TENANT-FOREIGN-ORG",
        display_name="Sec Cross Tenant Foreign Org",
        tenant_id=foreign_tenant.id,
    )
    organization_service._organization_repo.add(foreign_org_obj)
    services["session"].flush()

    auth_session_repo = services["auth_service"]._auth_session_repo
    live_session_id = services["user_session"].principal.session_id
    auth_session = auth_session_repo.get(live_session_id)
    auth_session.last_active_organization_id = foreign_org_obj.id
    auth_session_repo.update(auth_session)
    services["session"].flush()

    login_as(services, "sec-cross-tenant-user", "StrongPass123")

    assert services["tenant_context_service"].get_active_organization_id() != foreign_org_obj.id


# ----------------------------------------------------------------------
# 6. persisted still-authorized org restored successfully
# ----------------------------------------------------------------------


def test_persisted_still_authorized_organization_is_restored(services):
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-STILL-AUTH-A", display_name="Sec Still Auth A", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-still-auth-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)

    login_as(services, "sec-still-auth-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org_a.id)

    login_as(services, "sec-still-auth-user", "StrongPass123")

    assert services["tenant_context_service"].get_active_organization_id() == org_a.id


# ----------------------------------------------------------------------
# 7 & 8. multi-org: last=A restored when still authorized; not restored once revoked, B unaffected
# ----------------------------------------------------------------------


def test_user_with_a_and_b_access_restores_a_when_a_was_last_active(services):
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-MULTI-A", display_name="Sec Multi A", is_enabled=True
    )
    org_b = organization_service.create_organization(
        organization_code="SEC-MULTI-B", display_name="Sec Multi B", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-multi-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)
    _grant(services, user_id=user.id, organization_id=org_b.id)

    login_as(services, "sec-multi-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org_a.id)

    login_as(services, "sec-multi-user", "StrongPass123")

    assert services["tenant_context_service"].get_active_organization_id() == org_a.id


def test_revoking_a_while_retaining_b_does_not_restore_a_and_resolves_via_existing_policy(services):
    access = services["access_service"]
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-MULTI-REVOKE-A", display_name="Sec Multi Revoke A", is_enabled=True
    )
    org_b = organization_service.create_organization(
        organization_code="SEC-MULTI-REVOKE-B", display_name="Sec Multi Revoke B", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-multi-revoke-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)
    _grant(services, user_id=user.id, organization_id=org_b.id)

    login_as(services, "sec-multi-revoke-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org_a.id)

    _login_admin(services)
    access.remove_scope_grant(scope_type="organization", scope_id=org_a.id, user_id=user.id)

    login_as(services, "sec-multi-revoke-user", "StrongPass123")

    # A must not be restored. "Existing selection policy" (the sole-enabled-org auto-select,
    # reused unchanged, never a new "pick my other authorized org" mechanism) resolves to None
    # here since the tenant has more than one enabled organization -- exactly what a fresh
    # login with nothing persisted at all would also resolve to.
    active_id = services["tenant_context_service"].get_active_organization_id()
    assert active_id != org_a.id
    assert active_id is None

    # B remains fully accessible via an explicit switch -- revoking A never touched it.
    services["tenant_context_service"].set_active_organization(org_b.id)
    assert services["tenant_context_service"].get_active_organization_id() == org_b.id


# ----------------------------------------------------------------------
# 9. TenantMembership alone must not authorize an organization
# ----------------------------------------------------------------------


def test_tenant_membership_alone_does_not_authorize_a_specific_previously_granted_organization(services):
    """Distinct from the zero-explicit-grant/sole-enabled-org fallback (which stays -- see
    test 10): a user who has TenantMembership AND once had an explicit organization grant that
    was later revoked must not be treated as authorized for that SPECIFIC organization again
    merely by virtue of remaining a tenant member, when the tenant has other organizations too
    (so the sole-enabled-org fallback cannot itself explain a restore)."""
    access = services["access_service"]
    organization_service = services["organization_service"]
    org_a = organization_service.create_organization(
        organization_code="SEC-MEMBERSHIP-ONLY-A", display_name="Sec Membership Only A", is_enabled=True
    )
    organization_service.create_organization(
        organization_code="SEC-MEMBERSHIP-ONLY-B", display_name="Sec Membership Only B", is_enabled=True
    )
    user = _register_active_tenant_user(services, "sec-membership-only-user", role_names=["viewer"])
    _grant(services, user_id=user.id, organization_id=org_a.id)

    login_as(services, "sec-membership-only-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org_a.id)

    _login_admin(services)
    access.remove_scope_grant(scope_type="organization", scope_id=org_a.id, user_id=user.id)

    login_as(services, "sec-membership-only-user", "StrongPass123")

    # Still a tenant member (registration alone proves that), but organization access is gone.
    assert services["tenant_context_service"].get_active_organization_id() != org_a.id


# ----------------------------------------------------------------------
# 10. existing single-org login behavior remains correct
# ----------------------------------------------------------------------


def test_single_enabled_organization_zero_grant_auto_select_still_works(services):
    """The legitimate, product-accepted, pre-existing behavior this fix must NOT weaken: a user
    with NO organization-scoped RoleBinding at all, in a tenant with exactly one enabled
    organization, is still auto-selected into it -- because there is no PERSISTED value to
    (incorrectly) trust here in the first place; this path never goes through the new RBAC
    check at all, by construction."""
    default_org = services["tenant_context_service"].get_active_organization()
    assert default_org is not None

    user = services["auth_service"].register_user(
        "sec-single-org-zero-grant-user", "StrongPass123", role_names=["viewer"]
    )

    login_as(services, "sec-single-org-zero-grant-user", "StrongPass123")

    assert services["tenant_context_service"].get_active_organization_id() == default_org.id
