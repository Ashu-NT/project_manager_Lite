from __future__ import annotations

import pytest

from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError


def test_platform_runtime_application_service_tracks_active_organization_context(services):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    assert app_service.current_context_label() == "Default Organization"
    assert app_service.snapshot().context_label == "Default Organization"

    second = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_enabled=False,
    )
    # P10A: enabling and session-selecting are two separate, explicit steps --
    # PlatformRuntimeApplicationService.set_active_organization was deleted (it conflated
    # availability with session context); enabling goes through OrganizationService, selecting
    # goes through TenantContextService directly.
    organization_service.enable_organization(second.id)
    tenant_context_service.set_active_organization(second.id)

    assert app_service.current_context_label() == "North Division"
    assert app_service.get_active_organization() is not None
    assert app_service.get_active_organization().organization_code == "NORTH"


def test_platform_runtime_application_service_switches_module_mix_by_organization(services):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = app_service.get_active_organization()
    assert default_organization is not None

    second = organization_service.create_organization(
        organization_code="SOUTH",
        display_name="South Division",
        timezone_name="Africa/Lagos",
        base_currency="USD",
        is_enabled=False,
    )

    assert app_service.is_enabled("project_management") is True

    organization_service.enable_organization(second.id)
    tenant_context_service.set_active_organization(second.id)
    app_service.disable_module("project_management")
    assert app_service.is_enabled("project_management") is False

    tenant_context_service.set_active_organization(default_organization.id)
    assert app_service.current_context_label() == "Default Organization"
    assert app_service.is_enabled("project_management") is True


def test_platform_runtime_application_service_exposes_lifecycle_status_changes(services):
    app_service = services["platform_runtime_application_service"]

    trial = app_service.transition_module_lifecycle("project_management", "trial")
    assert trial.lifecycle_status == "trial"
    assert trial.runtime_enabled is True

    expired = app_service.transition_module_lifecycle("project_management", "expired")
    assert expired.lifecycle_status == "expired"
    assert expired.enabled is False
    assert expired.runtime_enabled is False
    assert app_service.is_enabled("project_management") is False


def test_platform_runtime_application_service_provisions_organization_with_initial_module_mix(services):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    default_organization = app_service.get_active_organization()
    assert default_organization is not None
    assert app_service.is_enabled("project_management") is True

    provisioned = app_service.provision_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="Africa/Lagos",
        base_currency="USD",
        is_enabled=False,
        initial_module_codes=[],
    )

    assert provisioned.organization_code == "OPS"
    assert app_service.get_active_organization() is not None
    assert app_service.get_active_organization().organization_code == "DEFAULT"
    assert app_service.is_enabled("project_management") is True

    organization_service.enable_organization(provisioned.id)
    tenant_context_service.set_active_organization(provisioned.id)
    assert app_service.current_context_label() == "Operations Hub"
    assert app_service.is_enabled("project_management") is False


def test_provision_organization_with_is_enabled_true_activates_in_one_transaction(services):
    """§18 item 6 -- dynamic confirmation that provision_organization's is_enabled=True branch is
    reachable and correct, not just statically plausible. P10A: provisioning with is_enabled=True
    still auto-selects the new organization into the provisioning caller's own session context,
    unchanged from pre-P10A behavior -- this is a deliberate provisioning/bootstrap convenience
    (PlatformRuntimeApplicationService.provision_organization's own post-commit step), distinct
    from the general-purpose organization switcher (P10C, not yet built)."""
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    default_organization = app_service.get_active_organization()
    assert default_organization is not None

    provisioned = app_service.provision_organization(
        organization_code="EAST",
        display_name="East Division",
        timezone_name="Asia/Dubai",
        base_currency="AED",
        is_enabled=True,
        initial_module_codes=["project_management"],
    )

    # Organization persisted enabled -- re-read the full list from the
    # repository, not the in-memory return value, so this actually confirms
    # the commit landed.
    all_orgs_by_id = {o.id: o for o in organization_service.list_organizations(enabled_only=None)}
    persisted = all_orgs_by_id[provisioned.id]
    assert persisted.is_enabled is True
    assert persisted.organization_code == "EAST"

    # Entitlements provisioned for the new organization.
    entitlements_by_code = {
        e.code: e for e in app_service.module_catalog_service.list_entitlements()
    }
    assert entitlements_by_code["project_management"].licensed is True
    assert entitlements_by_code["project_management"].enabled is True

    # Active runtime context updated -- both the tenant context service and
    # the application-service facade must agree the new organization is
    # active, with no manual session-switch follow-up call (unlike the
    # is_enabled=False provisioning test above, which requires one).
    assert tenant_context_service.get_active_organization_id() == provisioned.id
    assert app_service.get_active_organization().id == provisioned.id
    assert app_service.current_context_label() == "East Division"

    # P10A: no mutual exclusion -- the previously-active default organization
    # is still present AND still enabled, never forced disabled as a side
    # effect of another organization being provisioned/enabled.
    all_orgs_by_id = {o.id: o for o in organization_service.list_organizations(enabled_only=None)}
    still_there = all_orgs_by_id[default_organization.id]
    assert still_there.is_enabled is True


def test_switching_context_does_not_require_settings_manage(services):
    """P10A: `PlatformRuntimeApplicationService.set_active_organization` (settings.manage-gated)
    was deleted -- session-context switching goes through
    `TenantContextService.set_active_organization` directly, gated by RBAC organization access,
    never by the settings.manage admin permission. A user holding only `organization.access` (no
    `settings.manage`) can switch between organizations they are authorized for. Replaces the
    pre-P10A test asserting the opposite (that switching required settings.manage), which
    characterized behavior P10A deliberately removed -- session selection was never really an
    admin-permission-gated operation; it just used to ride along with the deleted
    OrganizationService.set_active_organization's own settings.manage requirement."""
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    user_session = services["user_session"]

    default_organization = tenant_context_service.get_active_organization()
    assert default_organization is not None
    second = organization_service.create_organization(
        organization_code="WEST",
        display_name="West Division",
        timezone_name="America/Chicago",
        base_currency="USD",
    )

    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="planner",
            display_name="Planner",
            role_names=frozenset(),
            permissions=frozenset({"organization.access"}),
            scoped_access={
                "organization": {
                    default_organization.id: frozenset({"organization.access"}),
                    second.id: frozenset({"organization.access"}),
                }
            },
            active_organization_id=default_organization.id,
        )
    )
    user_session.set_active_organization_id(default_organization.id)

    tenant_context_service.set_active_organization(second.id)

    assert tenant_context_service.get_active_organization() is not None
    assert tenant_context_service.get_active_organization().id == second.id


def test_switching_to_a_disabled_organization_is_denied(services):
    """P10A: the switch-time gate now checks `is_enabled`, never a mutual-exclusion designation --
    an organization the caller is otherwise authorized for still cannot be selected while
    disabled."""
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    user_session = services["user_session"]

    default_organization = tenant_context_service.get_active_organization()
    assert default_organization is not None
    second = organization_service.create_organization(
        organization_code="DISABLED-CTX",
        display_name="Disabled Context Org",
        timezone_name="America/Chicago",
        base_currency="USD",
        is_enabled=False,
    )

    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-2",
            username="planner-2",
            display_name="Planner Two",
            role_names=frozenset(),
            permissions=frozenset({"organization.access"}),
            scoped_access={
                "organization": {
                    default_organization.id: frozenset({"organization.access"}),
                    second.id: frozenset({"organization.access"}),
                }
            },
            active_organization_id=default_organization.id,
        )
    )
    user_session.set_active_organization_id(default_organization.id)

    with pytest.raises(BusinessRuleError):
        tenant_context_service.set_active_organization(second.id)

    assert tenant_context_service.get_active_organization().id == default_organization.id
