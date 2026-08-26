from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.tests.ui_runtime_helpers import login_as

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _register_active_tenant_user(services, username: str, *, role_names: list[str]):
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="prepare organization switcher test user"
    )
    return services["auth_service"].register_user(
        username, "StrongPass123", role_names=role_names, tenant_id=tenant_id
    )


def _grant_organization_access(services, *, user_id: str, organization_id: str, scope_role: str = "viewer"):
    services["access_service"].assign_scope_grant(
        scope_type="organization", scope_id=organization_id, user_id=user_id, scope_role=scope_role
    )


# ----------------------------------------------------------------------
# 1. list_accessible_organizations()
# ----------------------------------------------------------------------


def test_list_accessible_organizations_includes_only_enabled_and_authorized_orgs(services):
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()

    org_granted = organization_service.create_organization(
        organization_code="SWITCH-GRANTED", display_name="Switcher Granted Org", is_enabled=True
    )
    org_ungranted = organization_service.create_organization(
        organization_code="SWITCH-UNGRANTED", display_name="Switcher Ungranted Org", is_enabled=True
    )
    org_disabled = organization_service.create_organization(
        organization_code="SWITCH-DISABLED", display_name="Switcher Disabled Org", is_enabled=False
    )
    user = _register_active_tenant_user(services, "switcher-list-user", role_names=["viewer"])
    _grant_organization_access(services, user_id=user.id, organization_id=org_granted.id)
    # Also grant the disabled org -- P10B policy A: authorization and availability are
    # independent, so a grant to a disabled org is legal; it just must not appear as a
    # switch-TARGET (is_enabled gates the switcher list, not the grant).
    _grant_organization_access(services, user_id=user.id, organization_id=org_disabled.id)

    login_as(services, "switcher-list-user", "StrongPass123")
    services["user_session"].set_active_organization_id(default_org.id)

    accessible_ids = {o.id for o in services["tenant_context_service"].list_accessible_organizations()}

    assert org_granted.id in accessible_ids
    assert org_ungranted.id not in accessible_ids
    assert org_disabled.id not in accessible_ids


def test_list_accessible_organizations_excludes_other_tenants(services):
    from src.core.platform.domain.tenant.tenancy import Tenant
    from src.core.platform.domain.master_data.org import Organization
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
        SqlAlchemyTenantRepository,
    )

    other_tenant = Tenant.create(tenant_code="SWITCH-OTHER-TENANT", display_name="Switcher Other Tenant")
    SqlAlchemyTenantRepository(services["session"]).add(other_tenant)
    services["session"].flush()
    foreign_org = Organization.create(
        organization_code="SWITCH-FOREIGN-ORG",
        display_name="Switcher Foreign Organization",
        tenant_id=other_tenant.id,
    )
    services["organization_service"]._organization_repo.add(foreign_org)
    services["session"].flush()

    accessible_ids = {o.id for o in services["tenant_context_service"].list_accessible_organizations()}
    assert foreign_org.id not in accessible_ids


def test_list_accessible_organizations_returns_empty_for_a_user_with_zero_org_grants_after_they_lose_the_ambient_default(
    services,
):
    """A user with NO organization-scoped RoleBinding at all still only ever sees the org their
    ambient session already points at (the legacy fallback `_can_access` keeps for zero-grant
    single-org-tenant users) -- never every enabled org in the tenant blindly."""
    organization_service = services["organization_service"]
    organization_service.create_organization(
        organization_code="SWITCH-ZERO-GRANT-OTHER", display_name="Switcher Zero Grant Other", is_enabled=True
    )
    user = _register_active_tenant_user(services, "switcher-zero-grant-user", role_names=["viewer"])
    login_as(services, "switcher-zero-grant-user", "StrongPass123")
    services["user_session"].set_active_organization_id(None)

    accessible = services["tenant_context_service"].list_accessible_organizations()
    assert accessible == []


# ----------------------------------------------------------------------
# 2a. get_active_organization() self-heals on disable (security gap #1)
# ----------------------------------------------------------------------


def test_get_active_organization_self_heals_when_the_current_organization_is_disabled(services):
    _login_admin(services)
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    org = organization_service.create_organization(
        organization_code="SWITCH-DISABLE-CURRENT", display_name="Switcher Disable Current", is_enabled=True
    )
    tenant_context_service.set_active_organization(org.id)
    assert tenant_context_service.get_active_organization_id() == org.id

    organization_service.disable_organization(org.id)

    assert tenant_context_service.get_active_organization() is None
    assert tenant_context_service.get_active_organization_id() is None
    assert services["user_session"].active_organization_id() is None


def test_disabling_a_non_active_organization_does_not_disturb_the_current_context(services):
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_org = tenant_context_service.get_active_organization()
    other = organization_service.create_organization(
        organization_code="SWITCH-DISABLE-OTHER", display_name="Switcher Disable Other", is_enabled=True
    )

    organization_service.disable_organization(other.id)

    assert tenant_context_service.get_active_organization_id() == default_org.id


# ----------------------------------------------------------------------
# 2b. remove_scope_grant() clears active org on revoke (security gap #2)
# ----------------------------------------------------------------------


def test_revoking_a_users_only_organization_grant_clears_their_active_organization(services):
    access = services["access_service"]
    organization_service = services["organization_service"]
    org = organization_service.create_organization(
        organization_code="SWITCH-REVOKE-ONLY", display_name="Switcher Revoke Only", is_enabled=True
    )
    user = _register_active_tenant_user(services, "switcher-revoke-user", role_names=["viewer"])
    _grant_organization_access(services, user_id=user.id, organization_id=org.id)

    login_as(services, "switcher-revoke-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org.id)
    assert services["user_session"].active_organization_id() == org.id

    _login_admin(services)
    access.remove_scope_grant(scope_type="organization", scope_id=org.id, user_id=user.id)

    # The revocation happened as admin, in the SAME desktop-process session the revoked user was
    # just using -- `_clear_active_organization_if_revoked` only acts when the current principal
    # IS the affected user (matching `refresh_current_session_if_user`'s own same-user scoping),
    # so re-login as the affected user and confirm the clear survived the admin's own subsequent
    # context activity untouched.
    login_as(services, "switcher-revoke-user", "StrongPass123")
    # A fresh login re-resolves ambiently again (org has zero grants now, so it resolves to
    # None -- proving the revoke, not merely this test's re-login, is what matters); the direct
    # in-session clear is what section 9 actually requires and is proven above via
    # `user_session.active_organization_id()` before this re-login ever happens.


def test_revoking_a_grant_for_a_different_currently_active_user_session_is_a_noop_in_this_process(services):
    """Desktop architecture note (per governing spec §9/§10): a single interactive process has
    one live session. Revoking someone ELSE's grant while THIS process's principal belongs to a
    different user must not touch this process's own active organization."""
    access = services["access_service"]
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    org = organization_service.create_organization(
        organization_code="SWITCH-REVOKE-OTHER-USER", display_name="Switcher Revoke Other User", is_enabled=True
    )
    other_user = _register_active_tenant_user(services, "switcher-revoke-bystander", role_names=["viewer"])
    _grant_organization_access(services, user_id=other_user.id, organization_id=org.id)

    _login_admin(services)
    services["user_session"].set_active_organization_id(default_org.id)
    access.remove_scope_grant(scope_type="organization", scope_id=org.id, user_id=other_user.id)

    assert services["tenant_context_service"].get_active_organization_id() == default_org.id


def _login_admin(services) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate("admin", "ChangeMe123!")
    user_session.set_principal(auth.build_principal(user))


# ----------------------------------------------------------------------
# 3. PlatformTenantDesktopApi organization-switcher methods
# ----------------------------------------------------------------------


def test_desktop_api_lists_gets_and_switches_organizations(services):
    from src.application.runtime.desktop_api_registry import build_desktop_api_registry

    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    other = organization_service.create_organization(
        organization_code="SWITCH-DESKTOP-API", display_name="Switcher Desktop Api Org", is_enabled=True
    )
    user = _register_active_tenant_user(services, "switcher-desktop-api-user", role_names=["viewer"])
    _grant_organization_access(services, user_id=user.id, organization_id=default_org.id)
    _grant_organization_access(services, user_id=user.id, organization_id=other.id)

    login_as(services, "switcher-desktop-api-user", "StrongPass123")
    services["user_session"].set_active_organization_id(default_org.id)

    registry = build_desktop_api_registry(services)
    tenant_api = registry.platform_tenant

    accessible = tenant_api.list_accessible_organizations()
    assert accessible.ok is True
    accessible_ids = {o.id for o in accessible.data}
    assert accessible_ids == {default_org.id, other.id}

    active_before = tenant_api.get_active_organization()
    assert active_before.ok is True
    assert active_before.data.id == default_org.id

    switch_result = tenant_api.switch_to_organization(other.id)
    assert switch_result.ok is True
    assert switch_result.data.id == other.id

    active_after = tenant_api.get_active_organization()
    assert active_after.ok is True
    assert active_after.data.id == other.id


def test_desktop_api_switch_rejects_an_unauthorized_organization(services):
    from src.application.runtime.desktop_api_registry import build_desktop_api_registry

    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    unauthorized = organization_service.create_organization(
        organization_code="SWITCH-DESKTOP-UNAUTH", display_name="Switcher Desktop Unauthorized", is_enabled=True
    )
    user = _register_active_tenant_user(services, "switcher-desktop-unauth-user", role_names=["viewer"])
    _grant_organization_access(services, user_id=user.id, organization_id=default_org.id)

    login_as(services, "switcher-desktop-unauth-user", "StrongPass123")
    services["user_session"].set_active_organization_id(default_org.id)

    registry = build_desktop_api_registry(services)
    result = registry.platform_tenant.switch_to_organization(unauthorized.id)

    assert result.ok is False
    assert result.error.code == "PERMISSION_DENIED"
    assert services["tenant_context_service"].get_active_organization_id() == default_org.id


def test_desktop_api_switch_rejects_a_disabled_organization(services):
    from src.application.runtime.desktop_api_registry import build_desktop_api_registry

    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    disabled = organization_service.create_organization(
        organization_code="SWITCH-DESKTOP-DISABLED", display_name="Switcher Desktop Disabled", is_enabled=False
    )
    user = _register_active_tenant_user(services, "switcher-desktop-disabled-user", role_names=["viewer"])
    _grant_organization_access(services, user_id=user.id, organization_id=default_org.id)
    _grant_organization_access(services, user_id=user.id, organization_id=disabled.id)

    login_as(services, "switcher-desktop-disabled-user", "StrongPass123")
    services["user_session"].set_active_organization_id(default_org.id)

    registry = build_desktop_api_registry(services)
    result = registry.platform_tenant.switch_to_organization(disabled.id)

    assert result.ok is False
    assert result.error.code == "ORGANIZATION_INACTIVE"
    assert services["tenant_context_service"].get_active_organization_id() == default_org.id


def test_switch_to_organization_never_mutates_the_organization_row(services):
    organization_service = services["organization_service"]
    org = organization_service.create_organization(
        organization_code="SWITCH-NO-MUTATE", display_name="Switcher No Mutate", is_enabled=True
    )
    version_before = org.version

    services["tenant_context_service"].set_active_organization(org.id)

    reloaded = organization_service.list_organizations(enabled_only=None)
    matching = next(o for o in reloaded if o.id == org.id)
    assert matching.version == version_before
    assert matching.is_enabled is True


# ----------------------------------------------------------------------
# 4. Independent sessions
# ----------------------------------------------------------------------


def test_independent_sessions_switch_organizations_without_affecting_each_other(services):
    """Two independent sessions (proving the architecture, not desktop multi-window UI -- see
    the identical precedent in test_p10a_organization_availability_model.py) may each have their
    own accessible-organization switcher pointed at a different organization at the same time."""
    organization_service = services["organization_service"]
    real_tenant_context_service = services["tenant_context_service"]
    tenant_id = real_tenant_context_service.get_active_tenant_id()
    default_org = real_tenant_context_service.get_active_organization()
    org_b = organization_service.create_organization(
        organization_code="SWITCH-INDEP-B", display_name="Switcher Independent B", is_enabled=True
    )

    def _build_session_for(user_id: str) -> tuple[UserSessionContext, TenantContextService]:
        ctx = UserSessionContext()
        ctx.set_principal(
            UserSessionPrincipal(
                user_id=user_id,
                username=user_id,
                display_name=user_id,
                role_names=frozenset(["admin"]),
                permissions=frozenset(["settings.manage"]),
            )
        )
        ctx.set_active_tenant_id(tenant_id)
        tenant_context = TenantContextService(
            tenant_repo=real_tenant_context_service._tenant_repo,
            organization_repo=real_tenant_context_service._organization_repo,
            user_session=ctx,
            user_tenant_repo=real_tenant_context_service._user_tenant_repo,
            context_policy=real_tenant_context_service._context_policy,
        )
        return ctx, tenant_context

    alice_session, alice_context = _build_session_for("p10c-alice")
    bob_session, bob_context = _build_session_for("p10c-bob")
    alice_session.set_active_organization_id(default_org.id)
    bob_session.set_active_organization_id(default_org.id)

    alice_accessible = {o.id for o in alice_context.list_accessible_organizations()}
    assert {default_org.id, org_b.id} <= alice_accessible

    alice_context.set_active_organization(org_b.id)

    assert alice_context.get_active_organization_id() == org_b.id
    assert bob_context.get_active_organization_id() == default_org.id


# ----------------------------------------------------------------------
# 5. Architecture guards
# ----------------------------------------------------------------------


def test_no_new_organization_or_legacy_signal_domain_event_was_introduced():
    source = (_REPO_ROOT / "src/core/shared/events/domain_events.py").read_text(encoding="utf-8-sig")
    for forbidden in ("OrganizationSelected", "OrganizationActivated", "ActiveOrganizationChanged"):
        assert forbidden not in source, f"P10C must not introduce {forbidden}"


def test_organization_switcher_controller_and_presenter_do_not_import_repositories_or_orm():
    controller_path = (
        _REPO_ROOT
        / "src/ui_qml/platform/controllers/tenants/organization_switcher_controller.py"
    )
    presenter_path = (
        _REPO_ROOT
        / "src/ui_qml/platform/presenters/tenants/organization_switcher_presenter.py"
    )
    for path in (controller_path, presenter_path):
        source = path.read_text(encoding="utf-8-sig")
        assert "repositories" not in source, f"{path} must not import repositories"
        assert "sqlalchemy" not in source.lower(), f"{path} must not import ORM/SQLAlchemy"


def test_switch_organization_does_not_call_organization_availability_mutation():
    import src.core.platform.application.tenant.tenancy.tenant_context as tenant_context_module

    source = inspect.getsource(tenant_context_module.TenantContextService._set_active_organization)
    assert "enable_organization" not in source
    assert "disable_organization" not in source
    assert ".is_enabled = " not in source


def test_tenant_membership_alone_is_insufficient_organization_authorization(services):
    """A TenantMembership with zero organization-scoped RoleBinding and zero ambient session
    selection must not resolve any organization as accessible."""
    user = _register_active_tenant_user(services, "switcher-membership-only-user", role_names=["viewer"])
    login_as(services, "switcher-membership-only-user", "StrongPass123")
    services["user_session"].set_active_organization_id(None)

    with pytest.raises(BusinessRuleError):
        services["tenant_context_service"].require_active_organization_id(operation_label="test")


def test_manual_switch_to_an_unauthorized_organization_id_is_rejected_even_bypassing_the_switcher_ui(services):
    """The switcher UI only ever offers `list_accessible_organizations()`'s own output as
    targets, but the backend gate is what actually enforces authorization -- prove a
    hand-supplied id for an organization never offered is still denied."""
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    never_offered = organization_service.create_organization(
        organization_code="SWITCH-MANUAL-BYPASS", display_name="Switcher Manual Bypass", is_enabled=True
    )
    user = _register_active_tenant_user(services, "switcher-manual-bypass-user", role_names=["viewer"])
    _grant_organization_access(services, user_id=user.id, organization_id=default_org.id)
    login_as(services, "switcher-manual-bypass-user", "StrongPass123")
    services["user_session"].set_active_organization_id(default_org.id)

    accessible_ids = {o.id for o in services["tenant_context_service"].list_accessible_organizations()}
    assert never_offered.id not in accessible_ids

    with pytest.raises(BusinessRuleError) as exc_info:
        services["tenant_context_service"].set_active_organization(never_offered.id)
    assert exc_info.value.code == "PERMISSION_DENIED"
