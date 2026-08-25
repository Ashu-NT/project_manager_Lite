from __future__ import annotations

import pytest

from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError


def test_platform_runtime_application_service_tracks_active_organization_context(services):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]

    assert app_service.current_context_label() == "Default Organization"
    assert app_service.snapshot().context_label == "Default Organization"

    second = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )
    organization_service.set_active_organization(second.id)
    app_service.set_active_organization(second.id)

    assert app_service.current_context_label() == "North Division"
    assert app_service.get_active_organization() is not None
    assert app_service.get_active_organization().organization_code == "NORTH"


def test_platform_runtime_application_service_switches_module_mix_by_organization(services):
    app_service = services["platform_runtime_application_service"]
    default_organization = app_service.get_active_organization()
    assert default_organization is not None

    second = services["organization_service"].create_organization(
        organization_code="SOUTH",
        display_name="South Division",
        timezone_name="Africa/Lagos",
        base_currency="USD",
        is_active=False,
    )

    assert app_service.is_enabled("project_management") is True

    services["organization_service"].set_active_organization(second.id)
    app_service.set_active_organization(second.id)
    app_service.disable_module("project_management")
    assert app_service.is_enabled("project_management") is False

    services["organization_service"].set_active_organization(default_organization.id)
    app_service.set_active_organization(default_organization.id)
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

    default_organization = app_service.get_active_organization()
    assert default_organization is not None
    assert app_service.is_enabled("project_management") is True

    provisioned = app_service.provision_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="Africa/Lagos",
        base_currency="USD",
        is_active=False,
        initial_module_codes=[],
    )

    assert provisioned.organization_code == "OPS"
    assert app_service.get_active_organization() is not None
    assert app_service.get_active_organization().organization_code == "DEFAULT"
    assert app_service.is_enabled("project_management") is True

    services["organization_service"].set_active_organization(provisioned.id)
    app_service.set_active_organization(provisioned.id)
    assert app_service.current_context_label() == "Operations Hub"
    assert app_service.is_enabled("project_management") is False


def test_provision_organization_with_is_active_true_activates_in_one_transaction(services):
    """§18 item 6 -- dynamic confirmation that provision_organization's
    is_active=True branch is reachable and correct, not just statically
    plausible. Prior to P0.1 this branch always raised
    ORGANIZATION_INACTIVE; no existing test exercised is_active=True end
    to end through this method (every provisioning test in this file and
    test_platform_runtime_desktop_api.py used is_active=False)."""
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
        is_active=True,
        initial_module_codes=["project_management"],
    )

    # Organization persisted active -- re-read the full list from the
    # repository, not the in-memory return value, so this actually confirms
    # the commit landed.
    all_orgs_by_id = {o.id: o for o in organization_service.list_organizations(active_only=None)}
    persisted = all_orgs_by_id[provisioned.id]
    assert persisted.is_active is True
    assert persisted.organization_code == "EAST"

    # Entitlements provisioned for the new organization.
    entitlements_by_code = {
        e.code: e for e in app_service.module_catalog_service.list_entitlements()
    }
    assert entitlements_by_code["project_management"].licensed is True
    assert entitlements_by_code["project_management"].enabled is True

    # Active runtime context updated -- both the tenant context service and
    # the application-service facade must agree the new organization is
    # active, with no manual set_active_organization follow-up call (unlike
    # the is_active=False provisioning test above, which requires one).
    assert tenant_context_service.get_active_organization_id() == provisioned.id
    assert app_service.get_active_organization().id == provisioned.id
    assert app_service.current_context_label() == "East Division"

    # Transaction succeeded as a whole -- the previously-active default
    # organization is still present and merely no longer active, not lost.
    all_orgs_by_id = {o.id: o for o in organization_service.list_organizations(active_only=None)}
    still_there = all_orgs_by_id[default_organization.id]
    assert still_there.is_active is False


def test_platform_runtime_application_service_requires_settings_manage_to_switch_context(
    services,
):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    user_session = services["user_session"]

    default_organization = app_service.get_active_organization()
    assert default_organization is not None
    second = organization_service.create_organization(
        organization_code="WEST",
        display_name="West Division",
        timezone_name="America/Chicago",
        base_currency="USD",
        is_active=False,
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

    with pytest.raises(BusinessRuleError, match="settings.manage"):
        app_service.set_active_organization(second.id)

    assert app_service.get_active_organization() is not None
    assert app_service.get_active_organization().id == default_organization.id

